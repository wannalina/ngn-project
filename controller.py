from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
import networkx as nx
import threading
import json
from flask import Flask, request, jsonify

class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.net = nx.Graph()
        self.mac_to_port = {}
        self.dependencies = {}
        self.container_info = {}  # Store container information such as MAC and IP
        
        # Start Flask API server in a separate thread for registration
        self.start_flask_server()

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch()
        actions = []
        # drop traffic by default
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    def remove_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src = eth.src
        dst = eth.dst

        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src] = in_port

        if dst in self.mac_to_port[datapath.id]:
            out_port = self.mac_to_port[datapath.id][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # block unauthorized communication
        if src in self.dependencies and dst not in self.dependencies[src]:
            self.logger.info("Blocking unauthorized traffic from %s to %s", src, dst)
            return
        
        actions = [parser.OFPActionOutput(out_port)]
        
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPStateChange, MAIN_DISPATCHER)
    def _state_change_handler(self, ev):
        if ev.datapath not in self.net.nodes:
            self.net.add_node(ev.datapath.id)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        self.logger.info("Port status changed: %s", ev.msg)

    def get_shortest_path(self, src, dst):
        try:
            return nx.shortest_path(self.net, source=src, target=dst)
        except nx.NetworkXNoPath:
            return None

    def remove_flows_for_container(self, container_mac):
        for datapath_id, ports in self.mac_to_port.items():
            if container_mac in ports:
                datapath = self.net.nodes.get(datapath_id)
                if datapath:
                    match = datapath.ofproto_parser.OFPMatch(eth_dst=container_mac)
                    self.remove_flow(datapath, match)
                del self.mac_to_port[datapath_id][container_mac]
                self.logger.info("Removed flows for container %s", container_mac)

    def start_flask_server(self):
        # Start the Flask API server in a separate thread
        server_thread = threading.Thread(target=self.run_flask_app)
        server_thread.daemon = True
        server_thread.start()

    def run_flask_app(self):
        app = Flask(__name__)

        @app.route('/register', methods=['POST'])
        def register_container():
            # Receive registration data from containers
            data = request.json
            container_mac = data.get('mac')
            container_ip = data.get('ip')
            container_name = data.get('name')

            if container_mac and container_ip and container_name:
                self.container_info[container_mac] = {'ip': container_ip, 'name': container_name}
                self.logger.info(f"Container {container_name} registered with MAC {container_mac}")

                # Respond with a success message
                return jsonify({"message": "Registration successful"}), 200
            else:
                return jsonify({"message": "Invalid data"}), 400

        app.run(host='0.0.0.0', port=6000)

