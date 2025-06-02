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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # initialize variables for later
        is_allowed = False
        actions = ''
        src_host_name = ''
        dst_host_name = ''

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
        eth_type = eth.ethertype    # get packet type

        # learn MAC to port
        self.mac_to_port[dpid][src] = in_port

        # allow ARP packets through
        if eth_type == 0x0806:  # ARP header code
            self.logger.info("Allowing ARP packet")
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
            datapath.send_msg(out)
            return

        # get src/dst MAC addresses
        for host in self.hosts_mac_list:
            if host["mac"] == src:
                src_host_name = host["host_name"]
            if host["mac"] == dst: 
                dst_host_name = host["host_name"]
        
        # only allow packet if it's in the communication requirements (bidireactional)
        for req in self.communication_reqs:
            if req["host"] == src_host_name and dst_host_name in req["dependencies"]:
                is_allowed = True
                break
            if req["host"] == dst_host_name and src_host_name in req["dependencies"]:
                is_allowed = True
                break

        # if communication is allowed, add flow
        if is_allowed:
            self.logger.info("Packet in: %s -> %s ", src_host_name, dst_host_name)
            out_port = self.mac_to_port[dpid].get(dst)
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            
            self.logger.info(f"out port: {out_port}")

            if out_port is not None:
                actions = [parser.OFPActionOutput(out_port)]
            else:
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            self.add_flow(datapath, 1, match, actions)
            self.logger.info("Flow added: %s <--> %s", src_host_name, dst_host_name)

        else:
            self.logger.info("Packet dropped: %s -> %s (not in allowed dependencies)", src_host_name, dst_host_name)


    '''# event handler to handle topology change
    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)

        if dp.id in self.mac_to_port:
            self.delete_flow(dp)
            del self.mac_to_port[dp.id]'''

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

            for host in request_body:
                host_name = host['host']
                self.controller_app.hosts_info[host_name] = {
                    'mac': host['host_mac'],
                    'dpid': int(host['dpid'])
                }

            # iterate over all known hosts
            for host in request_body:
                # add host info to hosts list
                host_for_mac_list = {
                    "host_name": host["host"],
                    "mac": host["host_mac"]
                }
                self.controller_app.hosts_mac_list.append(host_for_mac_list)

                # add host to communication requirements list
                host_for_reqs = { "host": host["host"], "dependencies": [] }
                self.controller_app.communication_reqs.append(host_for_reqs)

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

            for host_name, info in self.controller_app.hosts_info.items():
                if host_name == host_del:
                    self.controller_app.logger.info(f"host name and stuff: {host_name}, {info["dpid"]}")
                    dpid = info["dpid"]
                    dpid_str = dpid_lib.dpid_to_str(dpid)
                    msg = 'Receive topology change event. Flush MAC table.'
                    self.logger.debug("[dpid=%s] %s", dpid_str, msg)

                    for dp in self.controller_app.mac_to_port:
                        if dpid in dp:
                            self.controller_app.delete_flow(dp)
                            del self.controller_app.mac_to_port[dp.id]
                            break
                    self.controller_app.logger.info(f"host: {host_name}, {info}")
                    break

            # remove hosts from communication requirements
            for req in self.controller_app.communication_reqs:
                # remove communication reqs from host
                if req["host"] == host_del:
                    req["dependencies"] = []
                
                # remove host from communication reqs
                if host_del in req["dependencies"]:
                    (req["dependencies"]).remove(host_del)

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