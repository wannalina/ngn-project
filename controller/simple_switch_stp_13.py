from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json

class SimpleSwitch13(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'stplib': stplib.Stp, 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        self.datapaths = {}
        self.hosts_info = {}

        config = {
            dpid_lib.str_to_dpid('0000000000000001'): {'bridge': {'priority': 0x8000}},
            dpid_lib.str_to_dpid('0000000000000002'): {'bridge': {'priority': 0x9000}},
            dpid_lib.str_to_dpid('0000000000000003'): {'bridge': {'priority': 0xa000}}
        }
        self.stp.set_config(config)

        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SimpleSwitch13RestController, {'switch_app': self})

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)

    def _install_flow_between(self, src_host, dst_host):
        src_info = self.hosts_info[src_host]
        dst_info = self.hosts_info[dst_host]

        for s_info, d_info in [(src_info, dst_info), (dst_info, src_info)]:
            dpid = s_info['dpid']
            datapath = self.datapaths.get(dpid)
            if not datapath:
                self.logger.warning(f"No datapath for DPID {dpid}")
                continue

            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto
            match = parser.OFPMatch(eth_src=s_info['mac'], eth_dst=d_info['mac'])
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

            self.logger.info(f"Installing flow: {s_info['mac']} -> {d_info['mac']} on DPID {dpid}")
            self.add_flow(datapath, 100, match, actions)

class SimpleSwitch13RestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitch13RestController, self).__init__(req, link, data, **config)
        self.switch_app = data['switch_app']

    @route('simple_switch', '/post-hosts', methods=['POST'])
    def post_hosts(self, req, **kwargs):
        body = req.json if req.body else {}
        for host in body:
            name = host['host']
            self.switch_app.hosts_info[name] = {
                'mac': host['host_mac'],
                'dpid': int(host['dpid'])
            }
        return Response(status=200, body="Hosts stored")

    @route('simple_switch', '/add-flow', methods=['POST'])
    def add_flow_route(self, req, **kwargs):
        body = req.json if req.body else {}
        src_host = body.get("host")
        dst_hosts = body.get("dependencies", [])

        if src_host not in self.switch_app.hosts_info:
            return Response(status=400, body=f"Unknown host: {src_host}")

        for dst in dst_hosts:
            if dst not in self.switch_app.hosts_info:
                continue
            self.switch_app._install_flow_between(src_host, dst)

        return Response(status=200, body="Flows added")
