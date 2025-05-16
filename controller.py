# Import Ryu libraries
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

# Import other libraries
import networkx as nx
import threading
from flask import Flask, request, jsonify


class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # Use OpenFlow 1.3

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)

        # Initialize network graph, MAC learning table, and container metadata
        self.net = nx.Graph()
        self.mac_to_port = {}
        self.dependencies = set()
        self.containers_list = []  # List of registered containers (MAC/IP/etc.)
        self.allowedDependencies = {}  # Mapping of allowed src-dst MAC pairs
        self.runningContainers = []

        # Start Flask server in background thread for REST API
        self.start_flask_server()

    def set_dependencies(self, dependencies):
        """Set allowed communication dependencies manually (unused here)."""
        self.dependencies = dependencies

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Configure switch to drop all packets by default (lowest-priority rule)."""
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()  # Match all packets
        actions = []  # No actions = drop

        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        """Add flow rule to switch."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=instructions)
        datapath.send_msg(mod)

    def remove_flow(self, datapath, match):
        """Remove a specific flow rule based on match."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

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
        """Handle packets not matched by existing flows (packet-in events)."""
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        # Parse Ethernet header
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src = eth.src
        dst = eth.dst

        # Learn source MAC -> port
        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src] = in_port

        # Always allow ARP packets
        if eth.ethertype == 0x0806:
            self.logger.debug("Allowing ARP packet from %s to %s", src, dst)
        else:
            # Enforce communication policy based on allowedDependencies
            allowed_dsts = self.allowedDependencies.get(src, [])
            if dst not in allowed_dsts:
                self.logger.info("Blocking unauthorized traffic from %s to %s", src, dst)
                return  # Drop packet

        # Determine output port for known or unknown destination
        out_port = self.mac_to_port[datapath.id].get(dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        # Install a new flow rule if destination is known
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # Send packet out manually
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPStateChange, MAIN_DISPATCHER)
    def _state_change_handler(self, ev):
        """Track connected datapaths (switches) in the graph."""
        if ev.datapath.id not in self.net.nodes:
            self.net.add_node(ev.datapath.id)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Log port status changes."""
        self.logger.info("Port status changed: %s", ev.msg)

    def get_shortest_path(self, src, dst):
        """Compute the shortest path between two switches (not used here)."""
        try:
            return nx.shortest_path(self.net, source=src, target=dst)
        except nx.NetworkXNoPath:
            return None

    def remove_flows_for_container(self, container_mac):
        """Remove all flow rules involving a specific container MAC."""
        for dpid, ports in self.mac_to_port.items():
            if container_mac in ports:
                datapath = self.net.nodes.get(dpid)
                if datapath:
                    match = datapath.ofproto_parser.OFPMatch(eth_dst=container_mac)
                    self.remove_flow(datapath, match)
                del self.mac_to_port[dpid][container_mac]
                self.logger.info("Removed flows for container %s", container_mac)

    def start_flask_server(self):
        """Launch Flask server in background thread."""
        server_thread = threading.Thread(target=self.run_flask_app)
        server_thread.daemon = True
        server_thread.start()

    def run_flask_app(self):
        """Define Flask REST API for registering and controlling containers."""
        app = Flask(__name__)

        @app.route('/', methods=['GET'])
        def default_path():
            return "Controller is running."

        @app.route('/register', methods=['POST'])
        def register_container():
            """Register a container (just records its name for now)."""
            data = request.get_json()
            container_name = data.get('container_name')

            if container_name:
                self.containers_list.append(container_name)
                return jsonify({"message": "Registration successful"}), 200
            return jsonify({"message": "Invalid data"}), 400

        @app.route('/add-dependencies', methods=['POST'])
        def add_dependencies():
            """Set allowed MAC-to-MAC communication."""
            data = request.get_json()
            if isinstance(data, dict):
                self.allowedDependencies = data
                print("Updated allowedDependencies:", self.allowedDependencies)
                return jsonify({"message": "Dependencies added"}), 200
            return jsonify({"message": "Invalid format"}), 400

        @app.route('/delete-dependencies', methods=['POST'])
        def remove_dependencies():
            """Remove specific or all allowed dependencies."""
            data = request.get_json()

            if isinstance(data, list) and len(data) == 1:
                # Remove a single container's dependencies
                container_name = data[0].get('container_name')
                to_remove = [k for k in self.allowedDependencies if k == container_name]
                for key in to_remove:
                    del self.allowedDependencies[key]
                return jsonify({"message": "Dependencies removed"}), 200

            elif isinstance(data, dict):
                # Reset all dependencies
                self.allowedDependencies = {}
                return jsonify({"message": "All dependencies cleared"}), 200

            return jsonify({"message": "Invalid format"}), 400

        # Start Flask server
        app.run(host='0.0.0.0', port=9000, threaded=True, use_reloader=False)
