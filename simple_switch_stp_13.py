# Enhanced simple_switch_stp_13.py with container dependency awareness

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.app import simple_switch_13
import socket
import threading
import json
import time

class DependencyAwareSwitch(simple_switch_13.SimpleSwitch13):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'stplib': stplib.Stp}

    def __init__(self, *args, **kwargs):
        super(DependencyAwareSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        
        # Container dependency management
        self.container_dependencies = {}  # {container_name: set(allowed_containers)}
        self.host_containers = {}  # {host_name: container_name}
        self.host_mac_mapping = {}  # {host_name: mac_address}
        self.allowed_communications = set()  # Set of (mac1, mac2) tuples
        
        # Socket server for receiving updates from NetworkManager
        self.control_socket = None
        self.setup_control_socket()
        
        # STP Configuration
        config = {dpid_lib.str_to_dpid('0000000000000001'):
                  {'bridge': {'priority': 0x8000}},
                  dpid_lib.str_to_dpid('0000000000000002'):
                  {'bridge': {'priority': 0x9000}},
                  dpid_lib.str_to_dpid('0000000000000003'):
                  {'bridge': {'priority': 0xa000}}}
        self.stp.set_config(config)

    def setup_control_socket(self):
        """Setup socket server for receiving dependency updates"""
        def socket_server():
            try:
                self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.control_socket.bind(('localhost', 9998))  # Different port from topology
                self.control_socket.listen(1)
                self.logger.info("Controller socket listening on port 9998")
                
                while True:
                    try:
                        conn, addr = self.control_socket.accept()
                        threading.Thread(target=self.handle_control_commands, args=(conn,)).start()
                    except Exception as e:
                        self.logger.error(f"Socket accept error: {e}")
                        break
            except Exception as e:
                self.logger.error(f"Failed to setup control socket: {e}")
        
        threading.Thread(target=socket_server, daemon=True).start()

    def handle_control_commands(self, conn):
        """Handle commands from NetworkManager"""
        while True:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                
                self.logger.info(f"Received command: {data}")
                
                if data.startswith("UPDATE_DEPENDENCIES"):
                    _, json_data = data.split(" ", 1)
                    dependencies = json.loads(json_data)
                    self.update_dependencies(dependencies)
                    conn.send("DEPENDENCIES_UPDATED".encode())
                    
                elif data.startswith("CONTAINER_STARTED"):
                    _, host, container = data.split()
                    self.add_container(host, container)
                    conn.send("CONTAINER_REGISTERED".encode())
                    
                elif data.startswith("CONTAINER_STOPPED"):
                    _, host, container = data.split()
                    self.remove_container(host, container)
                    conn.send("CONTAINER_UNREGISTERED".encode())
                    
                elif data.startswith("HOST_MAC_MAPPING"):
                    _, json_data = data.split(" ", 1)
                    mapping = json.loads(json_data)
                    self.host_mac_mapping.update(mapping)
                    conn.send("MAPPING_UPDATED".encode())
                    
            except Exception as e:
                self.logger.error(f"Error handling control command: {e}")
                break
        
        conn.close()

    def update_dependencies(self, dependencies):
        """Update container dependencies and recalculate allowed communications"""
        self.container_dependencies = dependencies
        self.recalculate_allowed_communications()
        self.update_flow_rules()
        self.logger.info(f"Updated dependencies: {dependencies}")

    def add_container(self, host, container):
        """Register a new container on a host"""
        self.host_containers[host] = container
        self.recalculate_allowed_communications()
        self.update_flow_rules()
        self.logger.info(f"Added container {container} on host {host}")

    def remove_container(self, host, container):
        """Unregister a container from a host"""
        if host in self.host_containers:
            del self.host_containers[host]
        self.recalculate_allowed_communications()
        self.update_flow_rules()
        self.logger.info(f"Removed container {container} from host {host}")

    def recalculate_allowed_communications(self):
        """Recalculate which hosts can communicate based on container dependencies"""
        self.allowed_communications.clear()
        
        # Allow communication between hosts based on container dependencies
        for host1, container1 in self.host_containers.items():
            for host2, container2 in self.host_containers.items():
                if host1 != host2:
                    # Check if containers can communicate
                    if self.can_containers_communicate(container1, container2):
                        mac1 = self.host_mac_mapping.get(host1)
                        mac2 = self.host_mac_mapping.get(host2)
                        if mac1 and mac2:
                            self.allowed_communications.add((mac1, mac2))
                            self.allowed_communications.add((mac2, mac1))  # Bidirectional
        
        self.logger.info(f"Allowed communications: {self.allowed_communications}")

    def can_containers_communicate(self, container1, container2):
        """Check if two containers are allowed to communicate"""
        # Check direct dependency
        if container2 in self.container_dependencies.get(container1, set()):
            return True
        if container1 in self.container_dependencies.get(container2, set()):
            return True
        
        # Allow same container type to communicate
        if container1 == container2:
            return True
            
        return False

    def update_flow_rules(self):
        """Update flow rules on all switches based on current allowed communications"""
        # Clear existing dependency-based flows and reinstall
        for datapath in self.mac_to_port.keys():
            dp = self.get_datapath(datapath)
            if dp:
                self.clear_dependency_flows(dp)
                self.install_dependency_flows(dp)

    def get_datapath(self, dpid):
        """Get datapath object by DPID"""
        # This would need to be implemented to get active datapaths
        # For now, we'll handle this in the packet_in handler
        return None

    def clear_dependency_flows(self, datapath):
        """Clear all dependency-based flow rules"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete all flows with priority 10 (our dependency flows)
        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=10,
            match=match
        )
        datapath.send_msg(mod)

    def install_dependency_flows(self, datapath):
        """Install flow rules based on current dependencies"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Install drop rules for unauthorized communications
        for src_mac in self.host_mac_mapping.values():
            for dst_mac in self.host_mac_mapping.values():
                if src_mac != dst_mac and (src_mac, dst_mac) not in self.allowed_communications:
                    # Install drop rule
                    match = parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
                    actions = []  # Empty actions = drop
                    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    mod = parser.OFPFlowMod(
                        datapath=datapath,
                        priority=10,  # Higher than normal learning rules
                        match=match,
                        instructions=inst
                    )
                    datapath.send_msg(mod)

    def delete_flow(self, datapath):
        """Enhanced delete flow to handle dependency flows"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Delete learning flows
        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)
        
        # Delete dependency flows
        self.clear_dependency_flows(datapath)

    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Enhanced packet handler with dependency checking"""
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

        # Learn MAC address
        self.mac_to_port[dpid][src] = in_port

        # Check if communication is allowed
        if not self.is_communication_allowed(src, dst):
            self.logger.info(f"Blocking communication from {src} to {dst}")
            return  # Drop the packet

        # Normal forwarding logic
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rule if not flooding
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # Use lower priority than dependency rules
            self.add_flow(datapath, 1, match, actions)

        # Send packet
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data
        )
        datapath.send_msg(out)

    def is_communication_allowed(self, src_mac, dst_mac):
        """Check if communication between two MAC addresses is allowed"""
        # Allow broadcast/multicast
        if dst_mac.startswith('ff:ff:') or dst_mac.startswith('01:'):
            return True
        
        # Allow same MAC (shouldn't happen but just in case)
        if src_mac == dst_mac:
            return True
        
        # Check against allowed communications
        return (src_mac, dst_mac) in self.allowed_communications

    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        """Handle topology changes"""
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)

        if dp.id in self.mac_to_port:
            self.delete_flow(dp)
            del self.mac_to_port[dp.id]
        
        # Reinstall dependency flows after topology change
        time.sleep(1)  # Wait for topology to stabilize
        self.install_dependency_flows(dp)

    @set_ev_cls(stplib.EventPortStateChange, MAIN_DISPATCHER)
    def _port_state_change_handler(self, ev):
        """Handle port state changes"""
        dpid_str = dpid_lib.dpid_to_str(ev.dp.id)
        of_state = {stplib.PORT_STATE_DISABLE: 'DISABLE',
                    stplib.PORT_STATE_BLOCK: 'BLOCK',
                    stplib.PORT_STATE_LISTEN: 'LISTEN',
                    stplib.PORT_STATE_LEARN: 'LEARN',
                    stplib.PORT_STATE_FORWARD: 'FORWARD'}
        self.logger.debug("[dpid=%s][port=%d] state=%s",
                          dpid_str, ev.port_no, of_state[ev.port_state])