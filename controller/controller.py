''' THIS CONTROLLER IMPLEMENTATION USES THE simple_switch_stp_13.py 
EXAMPLE AS A BASE FOR OUR OWN IMPLEMENTATION '''

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

# import other libraries (logging etc)
import json
import os
from datetime import datetime
import threading
import networkx as nx
from flask import Flask, request, jsonify


class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # use OpenFlow 1.3
    _CONTEXTS = {'stplib': stplib.Stp}

    # initialize SDN controller
    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        
        # packet logging
        self.log_dir = "packet_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # initialize network graph: nodes = switches (dpid), edges = links between switches
        self.net = nx.Graph()
        self.running_container_names = set()    # set of regitsered (running) container names
        self.communication_reqs = set()     # application communication requirements/dependencies
        self.allowed_dependencies = {}      # mapping of allowed src - dest MAC pairs

        #TODO: check this and modify
        # Sample of stplib config.
        #  please refer to stplib.Stp.set_config() for details.
        config = {dpid_lib.str_to_dpid('0000000000000001'):
                {'bridge': {'priority': 0x8000}},
                dpid_lib.str_to_dpid('0000000000000002'):
                {'bridge': {'priority': 0x9000}},
                dpid_lib.str_to_dpid('0000000000000003'):
                {'bridge': {'priority': 0xa000}}}
        self.stp.set_config(config)

    # function to log packet events and save logs in json file
    def log_packets(self, dpid, src, dst, in_port, action, pkt_type='unknown'):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "dpid": dpid,
            "src": src,
            "dst": dst,
            "in_port": in_port,
            "action": action,
            "packet_type": pkt_type
        }
        log_file = os.path.join(self.log_dir, "packet_events.json")
        with open(log_file, "a") as f:
            json.dump(log_entry, f)
            f.write("\n")

    # function to set communication requirements (dependencies) between applications
    def set_communication_reqs(self, dependencies):
        self.communication_reqs = dependencies
    
    '''
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority,
            match=match, instructions=inst
        )
        datapath.send_msg(mod)
    '''


    # function to remove flows based on matched dst MAC addresses
    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # iterate over all known dst MAC addresses for this datapath
        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)

            # delete flows with priority 1
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

        # log flow deletion
        self.log_packets(
            dpid=datapath.id,
            src="controller",
            dst="all",
            in_port=-1,
            action="delete_all_flows",
            pkt_type="flow"
        )

        # clear all MAC-to-port mappings for this datapath
        if datapath.id in self.mac_to_port:
            del self.mac_to_port[datapath.id]
        self.logger.info(f"Flow deleterd successfully for: {datapath.id}")

    # function to handle packets that do not match existing flows
    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        # parse eth header
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
        if eth.ethertype == 0x0806:
            self.log_packets(dpid, src, dst, in_port, "allowed", "ARP")
            self.logger.debug("Allowing ARP packet from %s to %s", src, dst)    # log allowed packet
        else:
            #! only allow communication between specified dependencies (else; drop by default)
            allowed_dsts = self.allowed_dependencies.get(src, [])
            self.log_packets(dpid, src, dst, in_port, "dropped", "other")   # log dropped packet
            if dst not in allowed_dsts:
                self.logger.info("Blocking unauthorized traffic from %s to %s", src, dst)
                return  # drop packet

        # check if output port is known
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # drop packet if no communication requirement specified
            self.logger.info("Destination %s unknown on dpid %s. Dropping.", dst, dpid)
            self.log_packets(dpid, src, dst, in_port, "dropped_unknown_dst", "other")   # log dropped packet
            return

        self.log_packets(dpid, src, dst, in_port, "allowed", "other")  # log allowed packet
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

    # function to handle topology change (switch/link failure/reconfig)
    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp  # datapath where topology change happened
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)

        # if switch MAC-to-port table exists in records
        if dp.id in self.mac_to_port:
            self.delete_flow(dp)            # delete flows
            del self.mac_to_port[dp.id]     # remove mac-to-port mapping

        # add flows for allowed communication after flushing
        for src, allowed_dsts in self.allowed_dependencies.items():
            for dst in allowed_dsts:
                src_port = self.mac_to_port.get(dp.id, {}).get(src)
                dst_port = self.mac_to_port.get(dp.id, {}).get(dst)
                if src_port and dst_port:
                    match = dp.ofproto_parser.OFPMatch(in_port=src_port, eth_dst=dst)
                    actions = [dp.ofproto_parser.OFPActionOutput(dst_port)]

                    # log addition of flow
                    self.log_packets(
                        dpid=dp.id,
                        src=src,
                        dst=dst,
                        in_port=src_port,
                        action="flow_reinstalled_after_topology_change",
                        packet_type="policy"
                    )

                    # re-add flow
                    self.add_flow(dp, 1, match, actions)

    # function to handle port state changes and log new state of port on a switch
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

    #TODO: function to compute shortest path between two switches
    def get_shortest_path(self, src, dst):
        try:
            return nx.shortest_path(self.net, source=src, target=dst)
        except nx.NetworkXNoPath:
            return None



    ''' FLASK APPLICATION '''

    # function to run flask app and define routes
    def run_flask_app(self):
        app = Flask(__name__)

        # base route to test controller
        @app.route('/', methods=['GET'])
        def default_route():
            return "Controller is running!"

        # route to register application to controller
        @app.route('/register', methods=['POST'])
        def register_container_route():
            try:
                request_body = request.json
                container_name = request_body.get('container_name')

                if not container_name: 
                    return jsonify({"message": "No contianer name provided"}), 400
                
                # add container name to list of running containers
                self.running_container_names.add(container_name)
                return jsonify({"message": "Application registered to controller successfully!"}), 200
            except Exception as e:
                return jsonify({"error": f"Error registering container to controller: {e}"}), 500

        # route to add communication requirement between apps
        @app.route('/add-dependency', methods=['POST'])
        def add_dependency_route():
            try:
                request_body = request.json
                # check if valid format
                if isinstance(request_body, dict): 
                    self.allowed_dependencies = request_body
                    print("Updated allowed_dependencies:", self.allowed_dependencies)
                    return jsonify({"message": "Dependencies added"}), 200

                return jsonify({"message": "Dependencies received in invalid format"}), 400
            except Exception as e:
                return jsonify({"error": f"Error adding communication requirement to controller: {e}"}), 500

        # route to remove allowed communication requirements
        @app.route('/delete-dependency', methods=['POST'])
        def remove_dependency_route():
            try:
                request_body = request.json

                # reomve dependencies of one container
                if isinstance(request_body, list) and len(request_body) == 1:
                    container_name = request_body[0].get('container_name')
                    self.running_container_names.remove(container_name)
                    to_remove = [k for k in self.allowed_dependencies if k == container_name]
                    for key in to_remove:
                        del self.allowed_dependencies[key]
                    return jsonify({"message": "Dependencies removed"}), 200

                # remove all dependencies
                elif isinstance(request_body, dict):
                    self.allowed_dependencies = {}
                    self.running_container_names.clear()
                    return jsonify({"message": "All dependencies removed"}), 200

                return jsonify({"message": "Dependencies were received in invalid format"}), 400
            except Exception as e:
                return jsonify({"error": f"Error deleting dependency from controller: {e}"}), 500

        # start Flask server
        app.run(host='10.0.2.15', port=9000, threaded=True, use_reloader=False)

    # function to launch flask app
    def start_flask_server(self):
        server_thread = threading.Thread(target=self.run_flask_app)
        server_thread.daemon = True
        server_thread.start()