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
        print("Starting Ryu controller")
        self.controller_process = subprocess.Popen(["ryu-manager", "simple_switch_stp_13.py"],stdout=open("ryu.log", "w"),stderr=subprocess.STDOUT)

    def stop_controller(self):
        if self.controller_process:
            print("Stopping Ryu controller")
            self.controller_process.terminate()
            self.controller_process.wait()

    def generate_topology(self, num_switches=5, num_hosts=10, links_prob=0.4):
        #self.topo = RandomTopo(num_switches, num_hosts, links_prob)
        self.topo=RandomTopo()
        hosts, switches = self.topo.build(num_switches, num_hosts, links_prob)
        return hosts,switches
        
    
    def build_network(self):
        self.net = Mininet(topo=self.topo, build=False)
        self.net.addController(self.controller)
        self.net.build()
       

    def start_network(self):
        self.start_controller()
        print("Starting Network")
        self.net.start()

    def open_cli(self):
        CLI(self.net)

    def stop_network(self):
        print("Shutting down")
        self.net.stop()
        self.stop_controller()
        subprocess.run(["mn","-c"])
    
    def get_host(self, host_name):
        return self.net.get(host_name)
        
#    example of dockers from topology1
#    host2 = net.get('h2')
#    host2.cmd('docker load -i /fake_apps/random_logger.tar')
#    host2.cmd('docker run -d --name random_logger_h2 --net=host random-logger')

    #container functions
    def start_container(self, host_name, container_name="database", image_path="/fake_apps/database/database.tar"):

        host = self.get_host(host_name)
        if not host:
            return False
        
        # Load Image
        host.cmd(f'docker load -i {image_path}')
        
        # CORRERE CORSA
        host.cmd(f'docker run -d --name {container_name}_{host_name} --net=host {container_name}')
        
    def stop_container(self, host_name, container_name="random_logger"):
        container_key = f"{host_name}_{container_name}" #key is combination of host + image name
        host = self.get_host(host_name)
        if host:
            host.cmd(f'docker rm -f {container_name}_{host_name}') #flag -f needed to stop exectuion before remotion
            return True
        return False
    
    def stop_all_containers(self):
        for host_name in self.net.hosts:
            host = self.get_host(host_name.name)
            if host:
                host.cmd('docker rm -f $(docker ps -a -q)')
        return True

# TEST NETWORK
if __name__ == '__main__':
    handler = NetworkManager()
    hosts,switches=handler.generate_topology(4, 8, 0.5) #CHANGE PARAMETERS HERE!
    handler.build_network()
    handler.start_network()
    
    #handler.start_container('h1')    

    while True:
        cmd = input("[cli] Open Mininet | [stop] Stop The Network | [1] boot whale | [2] kill whale | : ").strip().lower()
        
        if cmd == "cli":
            handler.open_cli()
        elif cmd == "stop":
            handler.stop_all_containers()
            handler.stop_network()
            break
        elif cmd == "1":
            handler.start_container('h1',"database_cities","/fake_apps/databases/database_cities/database_cities.tar")
            handler.start_container('h2',"random_logger","/fake_apps/random_logger/random_logger.tar")
            handler.start_container('h2', "cities_server", "/fake_apps/servers/cities_server/cities_server.tar")
        elif cmd == "2":
            handler.stop_container('h1', 'database_cities')
            handler.stop_container('h2')
            handler.stop_container('h2', 'cities_server')
        else:
            print("Please use 'cli' or 'stop'")
