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
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib.packet import ipv4, icmp

# import other libraries
from webob import Response

# class for SDN controller; extends SimpleSwitch13
class SDNController(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # use OpenFlow 1.3
    _CONTEXTS = {'stplib': stplib.Stp, 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}   # MAC learning table for each switch
        self.stp = kwargs['stplib']
        self.datapaths = {}     # track active switches
        self.hosts_info = {}    # hosts info received from gui.py
        self.hosts_mac_list = []
        self.communication_reqs = [] # application communication requirements

        # register REST API class to handle requests (HTTP)
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SDNRestController, {'controller_app': self})

        # sample of stplib config
        config = {dpid_lib.str_to_dpid('0000000000000001'):
                {'bridge': {'priority': 0x8000}},
                dpid_lib.str_to_dpid('0000000000000002'):
                {'bridge': {'priority': 0x9000}},
                dpid_lib.str_to_dpid('0000000000000003'):
                {'bridge': {'priority': 0xa000}}}
        self.stp.set_config(config)

    # function to delete flow when one container is shut down
    def delete_flow(self, datapath):
        try:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser

            for dst in self.mac_to_port[datapath.id].keys():
                match = parser.OFPMatch(eth_dst=dst)
                mod = parser.OFPFlowMod(
                    datapath, command=ofproto.OFPFC_DELETE,
                    out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                    priority=1, match=match)
                datapath.send_msg(mod)

            self.logger.info(f"Flow deleted on switch DPID {datapath}")
        except Exception as e:
            self.logger.info(f"Error deleting flow in controller: {e}")

    # function to delete all flows
    def delete_all_flows(self):
        # iterate over all datapaths and delete flow
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

    def is_communication_allowed(self, src_host_name, dst_host_name):
        """Check if communication between two hosts is allowed (host-level only)"""
        for req in self.communication_reqs:
            if req["host"] == src_host_name and dst_host_name in req["dependencies"]:
                return True
            if req["host"] == dst_host_name and src_host_name in req["dependencies"]:
                return True
        return False

    def get_host_name_by_mac(self, mac_addr):
        """Get host name by MAC address (only Mininet hosts)"""
        for host in self.hosts_mac_list:
            if host["mac"] == mac_addr:
                return host["host_name"]
        return None

    def install_bidirectional_flows(self, datapath, src_mac, dst_mac, src_port, dst_port):
        """Install flows for both directions of communication"""
        parser = datapath.ofproto_parser
        
        # Forward direction: src_mac -> dst_mac
        match_forward = parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
        actions_forward = [parser.OFPActionOutput(dst_port)]
        self.add_flow(datapath, 10, match_forward, actions_forward)
        self.logger.info(f"Installing forward flow: {src_mac} -> {dst_mac} out_port={dst_port}")
        
        # Reverse direction: dst_mac -> src_mac
        match_reverse = parser.OFPMatch(eth_src=dst_mac, eth_dst=src_mac)
        actions_reverse = [parser.OFPActionOutput(src_port)]
        self.add_flow(datapath, 10, match_reverse, actions_reverse)

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
        src = eth.src
        dst = eth.dst
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        eth_type = eth.ethertype

        # Learn MAC to port mapping
        self.mac_to_port[dpid][src] = in_port

        # Always allow ARP packets
        if eth_type == 0x0806:  # ARP
            self.logger.debug("Processing ARP packet")
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
            datapath.send_msg(out)
            return

        # Handle IPv4 packets (including ICMP)
        if eth_type == 0x0800:
            src_host_name = self.get_host_name_by_mac(src)
            dst_host_name = self.get_host_name_by_mac(dst)

            if self.is_communication_allowed(src_host_name, dst_host_name):
                self.logger.info(f"Allowing packet: {src_host_name} -> {dst_host_name}")
                # Learn the port for the source MAC
                self.mac_to_port[dpid][src] = in_port

                # If we know the output port for the destination, install flows
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                    actions = [parser.OFPActionOutput(out_port)]
                    self.install_bidirectional_flows(datapath, src, dst, in_port, out_port)
                    self.logger.info(f"Flow installed: {src_host_name} <-> {dst_host_name}")
                else:
                    out_port = ofproto.OFPP_FLOOD
                    actions = [parser.OFPActionOutput(out_port)]
                    self.logger.info(f"Flooding packet: {src_host_name} -> {dst_host_name}")

                # Always send the current packet out
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=msg.buffer_id if msg.buffer_id != ofproto.OFP_NO_BUFFER else ofproto.OFP_NO_BUFFER,
                    in_port=in_port,
                    actions=actions,
                    data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
                )
                datapath.send_msg(out)
            else:
                self.logger.info(f"Packet dropped: {src_host_name} -> {dst_host_name} (not allowed)")
                # Drop silently

        # LOG MAC PORT self.logger.info(f"PacketIn: dpid={dpid}, in_port={in_port}, src={src}, dst={dst}")
        # LOG MAC PORT self.logger.info(f"mac_to_port[{dpid}]: {self.mac_to_port[dpid]}")

    # event handler to handle port change
    @set_ev_cls(stplib.EventPortStateChange, MAIN_DISPATCHER)
    def _port_state_change_handler(self, ev):
        dpid_str = dpid_lib.dpid_to_str(ev.dp.id)
        of_state = {stplib.PORT_STATE_DISABLE: 'DISABLE',
                    stplib.PORT_STATE_BLOCK: 'BLOCK',
                    stplib.PORT_STATE_LISTEN: 'LISTEN',
                    stplib.PORT_STATE_LEARN: 'LEARN',
                    stplib.PORT_STATE_FORWARD: 'FORWARD'}
        self.logger.debug("[dpid=%s][port=%d] state=%s",
                        dpid_str, ev.port_no, of_state[ev.port_state])


# class for REST API communication between gui.py and SDN controller
class SDNRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNRestController, self).__init__(req, link, data, **config)
        self.controller_app = data['controller_app']

    # route to post hosts info (host MAC address, dpid)
    @route('simple_switch', '/post-hosts', methods=['POST'])
    def post_hosts(self, req, **kwargs):
        try:
            request_body = req.json if req.body else {}

            # Clear previous host info to avoid duplicates/stale entries
            self.controller_app.hosts_info.clear()
            self.controller_app.hosts_mac_list.clear()
            self.controller_app.communication_reqs.clear()

            for host in request_body:
                host_name = host['host']
                self.controller_app.hosts_info[host_name] = {
                    'mac': host['host_mac'],
                    'dpid': int(host['dpid'])
                }
                # Only add Mininet host MACs
                host_for_mac_list = {
                    "host_name": host["host"],
                    "mac": host["host_mac"]
                }
                self.controller_app.hosts_mac_list.append(host_for_mac_list)
                host_for_reqs = { "host": host["host"], "dependencies": [] }
                self.controller_app.communication_reqs.append(host_for_reqs)

            self.controller_app.logger.info(f"Registered {len(request_body)} hosts with controller")
            self.controller_app.logger.info(f"hosts_mac_list: {[h['mac'] for h in self.controller_app.hosts_mac_list]}")
            return Response(body="Hosts stored", status=200)
        except Exception as e: 
            print(f"Error sending host data to controller: {e}")
            return Response(body="Error storing hosts", status=500)

    # route to add flows between allowed hosts
    @route('simple_switch', '/add-flow', methods=['POST'])
    def add_flow_route(self, req, **kwargs):
        try: 
            request_body = req.json if req.body else {}

            # populate communication_reqs dependencies
            for host in self.controller_app.communication_reqs:
                if host["host"] == request_body["host"]:
                    host["dependencies"] = request_body["dependencies"]
                    self.controller_app.logger.info(f"Updated dependencies for {request_body['host']}: {request_body['dependencies']}")

            return Response(body="Flows added",status=200)
        except Exception as e: 
            print(f"Error adding flow from communication requirements: {e}")
            return Response(body="Error adding flows", status=500)

    # route to delete flows when applications shut down
    @route('simple_switch', '/delete-flow', methods=['POST'])
    def delete_flow_route(self, req, **kwargs):
        try:
            body = req.json if req.body else {}
            host_del = body.get("host")

            # Get host dpid from hosts_info
            dpid = None
            for host_name, info in self.controller_app.hosts_info.items():
                if host_name == host_del:
                    dpid = info["dpid"]
                    break

            if dpid is None:
                return Response(status=404, body=f"Host {host_del} not found")

            # Get datapath object for this dpid
            datapath = self.controller_app.datapaths.get(dpid)
            if datapath is None:
                return Response(status=404, body=f"No datapath found for dpid {dpid}")

            # Delete flows for this datapath
            self.controller_app.delete_flow(datapath)
            
            # Remove from mac_to_port if present
            if dpid in self.controller_app.mac_to_port:
                del self.controller_app.mac_to_port[dpid]

            # Remove from communication requirements
            for req in self.controller_app.communication_reqs:
                if req["host"] == host_del:
                    req["dependencies"] = []
                if host_del in req["dependencies"]:
                    req["dependencies"].remove(host_del)

            return Response(status=200, body="Flows deleted")
            
        except Exception as e:
            return Response(status=500, body=f"Error deleting flows: {e}")

    # route to delete all flows from controller upon all containers stopped
    @route('simple_switch', '/delete-all-flows', methods=['POST'])
    def delete_all_flows_route(self, req, **kwargs):
        try:
            self.controller_app.delete_all_flows()
            
            # remove communication reqs from all hosts
            for req in self.controller_app.communication_reqs:
                req["dependencies"] = []

            return Response(body="All flows deleted", status=200)
        except Exception as e:
            return Response(body=f"Error deleting all flows: {e}", status=500)