''' 
THIS CONTROLLER IS ADAPTED FROM RYU simple_switch_13
IMPORTANT ADDITIONS: 
- receive host data (MAC address, dpid) from gui
- block all communication by default
- add flows according to defined application communication requirements (ARP + IPv4 only between allowed pairs)
'''

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response

import json

class SDNController(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.hosts_info = {}
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SDNRestController, {'switch_app': self})

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    def delete_all_flows(self):
        for dpid, datapath in self.datapaths.items():
            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto
            match = parser.OFPMatch()
            mod = parser.OFPFlowMod(
                datapath=datapath,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=match
            )
            datapath.send_msg(mod)
            self.logger.info(f"Deleted all flows on switch DPID {dpid}")

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
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id,
                in_port=in_port, actions=actions, data=msg.data)
            datapath.send_msg(out)
        else:
            self.logger.info(f"Dropping packet from {src} to {dst} — not allowed")
            return

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

            # ARP flow
            match_arp = parser.OFPMatch(
                eth_type=0x0806, eth_src=s_info['mac'])
            actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            self.add_flow(datapath, 10, match_arp, actions_arp)

            # IPv4 flow
            match_ip = parser.OFPMatch(
                eth_type=0x0800, eth_src=s_info['mac'], eth_dst=d_info['mac'])
            actions_ip = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            self.add_flow(datapath, 20, match_ip, actions_ip)

            self.logger.info(f"Installed ARP and IP flow: {s_info['mac']} -> {d_info['mac']} on DPID {dpid}")

class SDNRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNRestController, self).__init__(req, link, data, **config)
        self.switch_app = data['switch_app']

    @route('simple_switch', '/post-hosts', methods=['POST'])
    def post_hosts(self, req, **kwargs):
        try:
            request_body = req.json if req.body else {}
            for host in request_body:
                host_name = host['host']
                self.switch_app.hosts_info[host_name] = {
                    'mac': host['host_mac'],
                    'dpid': int(host['dpid'])
                }
            return Response(body="Hosts stored", status=200)
        except Exception as e:
            print(f"Error sending host data to controller: {e}")
            return Response(body="Error storing hosts", status=500)

    @route('simple_switch', '/add-flow', methods=['POST'])
    def add_flow_route(self, req, **kwargs):
        try: 
            request_body = req.json if req.body else {}
            src_host = request_body.get("host")
            dst_hosts = request_body.get("dependencies", [])

            if src_host not in self.switch_app.hosts_info:
                return Response(body=f"Unknown host: {src_host}", status=400)

            for dst in dst_hosts:
                if dst not in self.switch_app.hosts_info:
                    continue
                self.switch_app._install_flow_between(src_host, dst)

            return Response(body="Flows added",status=200)
        except Exception as e: 
            print(f"Error adding flow from communication requirements: {e}")
            return Response(body="Error adding flows", status=500)

    @route('simple_switch', '/delete-all-flows', methods=['POST'])
    def delete_all_flows_route(self, req, **kwargs):
        try:
            self.switch_app.delete_all_flows()
            return Response(body="All flows deleted", status=200)
        except Exception as e:
            return Response(body=f"Error deleting all flows: {e}", status=500)
