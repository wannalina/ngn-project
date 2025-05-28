''' THIS CONTROLLER IMPLEMENTATION USES THE simple_switch_stp_13.py 
EXAMPLE AS A BASE FOR OUR OWN IMPLEMENTATION '''

# import ryu libraries
from ryu.base import app_manager
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app.wsgi import ControllerBase, route,  WSGIApplication

# import other libraries (logging, etc)
import json

# class to define/handle controller functions
class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # use OpenFlow 1.3
    _CONTEXTS = {'stplib': stplib.Stp, 'wsgi':  WSGIApplication}

    # intialize SDN controller
    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(SDNControllerAPI, {'sdn_controller': self})
        self.hosts = []     # network hosts list
        self.allowed_communication = [] # allowed communication between hosts

        #??
        config = {dpid_lib.str_to_dpid('0000000000000001'):
                {'bridge': {'priority': 0x8000}},
                dpid_lib.str_to_dpid('0000000000000002'):
                {'bridge': {'priority': 0x9000}},
                dpid_lib.str_to_dpid('0000000000000003'):
                {'bridge': {'priority': 0xa000}}}
        self.stp.set_config(config)

    # function to add new flow to controller
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

    # function to delete flow from controller
    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    # function to check allowed destinations
    def check_allowed_dsts(self, src):
        allowed_dsts = []
        for entry in self.allowed_communication:
            if entry['host'] == src:
                allowed_dsts.extend(entry['dependencies'])
        return allowed_dsts

    # function to handle packets with no existing flow
    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        print("logging??")

        # parse the header
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn mac address to avoid FLOOD next time
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # always allow ARP packets through
        '''if eth.ethertype == 0x0806:
            self.logger.debug("Allowing ARP packet from %s to %s", src, dst)    # log allowed packet
        else:
            #! only allow communication between specified hosts; else drop by default
            allowed_dsts = self.check_allowed_dsts(src)
            print("allowed dsts:", allowed_dsts)
            if dst not in allowed_dsts:
                self.logger.info("Blocking unauthorized traffic from %s to %s", src, dst)
                return  # drop packet '''

        # check if output port is known
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # drop packet if no communication requirement specified
            self.logger.info("Destination %s unknown on dpid %s. Dropping.", dst, dpid)
            return

        actions = [parser.OFPActionOutput(out_port)]

        #! add flow for allowed dependency (avoids packet_in occurring again)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # extract packet data if no buffer ID
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # send data packet out
        out = parser.OFPPacketOut(
            datapath=datapath, 
            buffer_id=msg.buffer_id,
            in_port=in_port, 
            actions=actions, 
            data=data
        )
        datapath.send_msg(out)

    # function to loisten to/handle topology change
    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)

        if dp.id in self.mac_to_port:
            self.delete_flow(dp)
            del self.mac_to_port[dp.id]

    # function to listen to/handle port change events
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


# class to handle API calls for flow adding/removal
class SDNControllerAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNControllerAPI, self).__init__(req, link, data, **config)
        self.controller = data['sdn_controller']

    # function to get communication requirements as MAC addresses
    def get_host_to_mac(self, request_body):
        reqs_mac = []
        host_mac = ""
        for host in self.controller.hosts:
            if host["host"] == request_body["host"]: 
                host_mac = host["host_mac"]
            for host_req in request_body["dependencies"]:
                if host["host"] == host_req:
                    host_req_mac = host["host_mac"]
                    reqs_mac.append(host_req_mac)
            req_object = {
                "host": host_mac,
                "dependencies": reqs_mac
            }
            self.controller.allowed_communication.append(req_object)

    # route to save hosts list in controller
    @route('post-hosts', '/post-hosts', methods=['POST'])
    def post_hosts_list(self, req, **kwargs):
        try: 
            request_body = req.json

            # Access the main controller instance
            self.controller.hosts = request_body

            return 'Hosts list saved in controller successfully.'
        except Exception as e:
            return f'Error saving hosts in controller: {e}'

    # route to add flows between started containers
    @route('add-flow', '/add-flow', methods=['POST'])
    def add_communication_reqs(self, req, **kwargs):
        host = {}
        try:
            request_body = req.json
            for h in self.controller.hosts:
                if h['host'] == request_body['host']:
                    host = h
            print('h:', host)
            if request_body['dependencies']:
                self.get_host_to_mac(request_body)
            self.controller.add_flow(host['dpid'], 1, match, actions)
            #self.controller.self.add_flow(datapath, 1, match, actions)
            return "Flows added to controller successfully."
        except Exception as e:
            return f'Error adding flows to controller.'