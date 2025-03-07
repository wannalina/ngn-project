from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
import random
from topologies.topology_generator import RandomTopo
import subprocess

class NetworkManager:
    def __init__(self):
        self.topo = None
        self.net = None
        self.controller = RemoteController('c1', ip='127.0.0.1', port=6633)

    def start_controller(self):
        print("Starting Ryu controller...")
        self.controller_process = subprocess.Popen(["ryu-manager", "simple_switch_stp_13.py"],stdout=open("ryu.log", "w"),stderr=subprocess.STDOUT)

    def stop_controller(self):
        if self.controller_process:
            print("Stopping Ryu controller...")
            self.controller_process.terminate()
            self.controller_process.wait()

    def create_network(self, num_switches=5, num_hosts=10, links_prob=0.4):
        self.topo = RandomTopo(num_switches, num_hosts, links_prob)
        self.net = Mininet(topo=self.topo, build=False)
        self.net.addController(self.controller)
        self.net.build()

    def start_network(self):
        self.start_controller()
        print("Starting Network...")
        self.net.start()

    def open_cli(self):
        CLI(self.net)

    def stop_network(self):
        print("Shutting down...")
        self.net.stop()
        self.stop_controller()
        subprocess.run(["mn","-c"])

# TEST NETWORK
if __name__ == '__main__':
    handler = NetworkManager()
    handler.create_network(4, 8, 0.5) #CHANGE PARAMETERS HERE!
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