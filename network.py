from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
import random
from topologies.topology_generator import RandomTopo


class NetworkManager:
    def __init__(self):
        self.topo = None
        self.net = None
        self.controller = RemoteController('c1', ip='127.0.0.1', port=6633)

    def create_network(self, num_switches=5, num_hosts=10, links_prob=0.4):
        self.topo = RandomTopo(num_switches, num_hosts, links_prob)
        self.net = Mininet(topo=self.topo, build=False)
        self.net.addController(self.controller)
        self.net.build()

    def start_network(self):
        print("Starting Network...")
        self.net.start()

    def open_cli(self):
        CLI(self.net)

    def stop_network(self):
        print("Shutting down...")
        self.net.stop()


# TEST NETWORK
if __name__ == '__main__':
    handler = NetworkManager()
    handler.create_network(4, 8, 0.5)
    handler.start_network()
    
    while True:
        cmd = input("[cli] Open Mininet | [stop] Stop The Network: ").strip().lower()
        
        if cmd == "cli":
            handler.open_cli()
        elif cmd == "stop":
            handler.stop_network()
            break
        else:
            print("Please use 'cli' or 'stop'")