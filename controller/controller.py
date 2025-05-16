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

    #TODO: function to remove flows based on match
    def delete_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

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
            allowed_dsts = self.allowedDependencies.get(src, [])
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

        self.log_packet_event(dpid, src, dst, in_port, "allowed", "other")  # log allowed packet
        actions = [parser.OFPActionOutput(out_port)]

        # add flow for allowed dependency (avoids packet_in occurring again)
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

    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.debug("[dpid=%s] %s", dpid_str, msg)

        if dp.id in self.mac_to_port:
            self.delete_flow(dp)
            del self.mac_to_port[dp.id]

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
