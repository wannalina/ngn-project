''' 
THIS CONTROLLER IS ADAPTED FROM RYU simple_switch_stp_13
IMPORTANT ADDITIONS: 
- receive host data (MAC address, dpid) from gui
- block all communication by default
- add flows according to defined application communication requirements
'''

# import ryu libraries
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

# import other libraries
import json

# class for SDN controller; extends SimpleSwitch13
class SDNController(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # use OpenFlow version 1.3
    _CONTEXTS = {'stplib': stplib.Stp, 'wsgi': WSGIApplication}     # specify required contexts; spanning tree and wsgi (REST API)

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}   # MAC learning table for each switch
        self.stp = kwargs['stplib']     # spanning tree protocol (prevents loops)
        self.datapaths = {}     # track active switches
        self.hosts_info = {}    # hosts info received from gui.py

        # assign bridge priorities for stp
        config = {
            dpid_lib.str_to_dpid('0000000000000001'): {'bridge': {'priority': 0x8000}},
            dpid_lib.str_to_dpid('0000000000000002'): {'bridge': {'priority': 0x9000}},
            dpid_lib.str_to_dpid('0000000000000003'): {'bridge': {'priority': 0xa000}}
        }
        self.stp.set_config(config)

        # register REST API class to handle requests (HTTP)
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SDNRestController, {'switch_app': self})

    # function to add new OpenFlow rule to switch
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    # function to delete all flows
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

    # event handler for packet in events (learn MAC addresses)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        self.datapaths[datapath.id] = datapath  # track datapath
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

        self.mac_to_port[dpid][src] = in_port   # learn source MAC address

        # if 
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
            # drop packet
            self.logger.info(f"Dropping packet from {src} to {dst} — not allowed")


        # send the allowed packet out
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)

    # function to install flow between allowed applications
    def _install_flow_between(self, src_host, dst_host):
        src_info = self.hosts_info[src_host]
        dst_info = self.hosts_info[dst_host]

        # add new flow in both directions (src --> dst AND dst --> src)
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

# class for REST API communication between gui.py and SDN controller
class SDNRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNRestController, self).__init__(req, link, data, **config)
        self.switch_app = data['switch_app']

    # route to post hosts info (host MAC address, dpid)
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

    # route to add flows between allowed hosts
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

    # route to delete flows when applications shut down
    @route('simple_switch', '/delete-flows', methods=['POST'])
    def delete_flow_route(self, req, **kwargs):
        try:
            body = req.json if req.body else {}
            src_host = body.get("host")
            dst_hosts = body.get("dependencies", [])

            for dst in dst_hosts:
                for s_info, d_info in [
                    (self.switch_app.hosts_info.get(src_host), self.switch_app.hosts_info.get(dst)),
                    (self.switch_app.hosts_info.get(dst), self.switch_app.hosts_info.get(src_host))
                ]:
                    if not s_info or not d_info:
                        continue
                    datapath = self.switch_app.datapaths.get(s_info['dpid'])
                    if not datapath:
                        continue

                    parser = datapath.ofproto_parser
                    ofproto = datapath.ofproto
                    match = parser.OFPMatch(eth_src=s_info['mac'], eth_dst=d_info['mac'])

                    mod = parser.OFPFlowMod(
                        datapath=datapath, match=match,
                        command=ofproto.OFPFC_DELETE,
                        out_port=ofproto.OFPP_ANY,
                        out_group=ofproto.OFPG_ANY
                    )
                    datapath.send_msg(mod)

            return Response(status=200, body="Flows deleted")
        except Exception as e:
            return Response(status=500, body=f"Error deleting flows: {e}")

    # route to delete all flows from controller upon all containers stopped
    @route('simple_switch', '/delete-all-flows', methods=['POST'])
    def delete_all_flows_route(self, req, **kwargs):
        try:
            self.switch_app.delete_all_flows()
            return Response(body="All flows deleted", status=200)
        except Exception as e:
            return Response(body=f"Error deleting all flows: {e}", status=500)

