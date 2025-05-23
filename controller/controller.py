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
import threading
from webob import Response
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

    # function to handle packets with no existing flow
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

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    # function to loisten to/handle topology change
    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)
        
        print("hosts list:", self.hosts)

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

    # route to save hosts list in controller
    @route('post-hosts', '/post-hosts', methods=['POST'])
    def post_hosts_list(self, req, **kwargs):
        try: 
            request_body = req.json if req.body else {}
            print("Request:", request_body)

            # Access the main controller instance
            self.controller.hosts = request_body

            return {"message": 'Hosts list saved in controller successfully.'}, 200
        except Exception as e:
            return {"error": f'Error saving hosts in controller: {e}'}, 500

    '''
    # function to run flask app and define routes
    def run_flask_app(self):
        app = Flask(__name__)

        # base route to test controller
        @app.route('/', methods=['GET'])
        def default_route():
            return "Controller is running!"

        # route to save hosts list in controller upon network startup
        @app.route('/post-hosts', methods=['POST'])
        def add_hosts_to_controller():
            try: 
                request_body = request.json
                print("Request:", request_body)
                self.hosts = request_body
                return jsonify({'message': 'Hosts list saved in controller successfully.'}), 200
            except Exception as e:
                return jsonify({'error': 'Error saving hosts in controller.'}), 500

        # route to register application to controller
        @app.route('/register', methods=['POST'])
        def register_container_route():
            try:
                #TODO: implement
                return jsonify({"message": "Application registered to controller successfully!"}), 200
            except Exception as e:
                return jsonify({"error": f"Error registering container to controller: {e}"}), 500

        # route to add flow to controller
        @app.route('/add-flow', methods=['POST'])
        def add_dependency_route():
            try:
                request_body = request.json
                #TODO: implement
                return jsonify({"message": "Flow added to controller successfully."}), 200
            except Exception as e:
                return jsonify({"error": f"Error adding flow to controller: {e}"}), 500

        # route to remove allowed communication requirements
        @app.route('/delete-dependency', methods=['POST'])
        def remove_dependency_route():
            try:
                request_body = request.json
                #TODO: implement
                return jsonify({'message': 'Flow deleted from controller successfully.'}), 200
            except Exception as e:
                return jsonify({"error": f"Error removing flow from controller: {e}"}), 500

        # start Flask server
        app.run(host='0.0.0.0', port=9000, threaded=True, use_reloader=False)

    # function to launch flask app
    def start_flask_server(self):
        server_thread = threading.Thread(target=self.run_flask_app)
        server_thread.daemon = True
        server_thread.start()
    '''
