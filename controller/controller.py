
from ryu.base import app_manager
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet, ethernet
from ryu.app.wsgi import ControllerBase, route, WSGIApplication

import json

class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'stplib': stplib.Stp, 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SDNControllerAPI, {'sdn_controller': self})
        self.hosts = []
        self.allowed_communication = []

        config = {
            dpid_lib.str_to_dpid('0000000000000001'): {'bridge': {'priority': 0x8000}},
            dpid_lib.str_to_dpid('0000000000000002'): {'bridge': {'priority': 0x9000}},
            dpid_lib.str_to_dpid('0000000000000003'): {'bridge': {'priority': 0xa000}}
        }
        self.stp.set_config(config)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for dst in self.mac_to_port.get(datapath.id, {}).keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    def check_allowed_dsts(self, src):
        allowed_dsts = []
        for entry in self.allowed_communication:
            if entry['host'] == src:
                allowed_dsts.extend(entry['dependencies'])
        return allowed_dsts

    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        allowed_dsts = self.check_allowed_dsts(src)
        if dst not in allowed_dsts:
            self.logger.info("Blocking unauthorized traffic from %s to %s", src, dst)
            return

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            return

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
        self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)

    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        if dp.id in self.mac_to_port:
            self.delete_flow(dp)
            del self.mac_to_port[dp.id]

    @set_ev_cls(stplib.EventPortStateChange, MAIN_DISPATCHER)
    def _port_state_change_handler(self, ev):
        pass

class SDNControllerAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNControllerAPI, self).__init__(req, link, data, **config)
        self.controller = data['sdn_controller']

    @route('post-hosts', '/post-hosts', methods=['POST'])
    def post_hosts_list(self, req, **kwargs):
        try:
            request_body = req.json
            self.controller.hosts = request_body
            return 'Hosts list saved in controller successfully.'
        except Exception as e:
            return f'Error saving hosts: {e}'

    @route('add-flow', '/add-flow', methods=['POST'])
    def add_communication_reqs(self, req, **kwargs):
        try:
            request_body = req.json
            host_mac = ""
            reqs_mac = []

            for host in self.controller.hosts:
                if host["host"] == request_body["host"]:
                    host_mac = host["host_mac"]

                for dep in request_body["dependencies"]:
                    if host["host"] == dep:
                        reqs_mac.append(host["host_mac"])

            req_object = {
                "host": host_mac,
                "dependencies": reqs_mac
            }
            self.controller.allowed_communication.append(req_object)

            return "Communication requirements updated."
        except Exception as e:
            return f"Error updating communication requirements: {e}"
