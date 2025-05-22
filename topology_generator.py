# Enhanced topology_generator.py with MAC address support

import subprocess
import threading
import socket
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
import random
import sys
import json

class RandomTopo(Topo):
    def build(self, num_switches=0, num_hosts=0, links_prob=0.5):
        switches = []
        hosts = []
        
        # Add switches
        for s in range(1, num_switches + 1):
            switch = self.addSwitch(f's{s}')
            switches.append(switch)
        
        # Add hosts and connect to switches
        for h in range(1, num_hosts + 1):
            host = self.addHost(f'h{h}')
            hosts.append(host)
            # Randomly select 1 switch
            switch = random.choice(switches)
            self.addLink(host, switch)

        # Linear connectivity
        for i in range(len(switches) - 1):
            self.addLink(switches[i], switches[i + 1])
        
        # Random extra connectivity
        for i in range(len(switches)):
            for j in range(i + 2, len(switches)):  # skip close switches
                if random.random() < links_prob:
                    self.addLink(switches[i], switches[j])

class NetworkServer:
    def __init__(self, net):
        self.net = net
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('localhost', 9999))
        self.sock.listen(1)
        print("Socket server is now listening on localhost:9999")

    def handle_commands(self, conn):
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                print(f"Received command: {data}")

                if data.startswith("START_CONTAINER"):
                    _, host, container, image = data.split()
                    self.start_container(host, container, image)
                    conn.send("CONTAINER_STARTED".encode())
                    
                elif data.startswith("STOP_CONTAINER"):
                    _, host, container = data.split()
                    self.stop_container(host, container)
                    
                elif data == "STOP_ALL":
                    self.stop_all_containers()
                    
                elif data == "SHUTDOWN":
                    print("Received shutdown command")
                    self.stop_all_containers()
                    conn.close()
                    self.sock.close()
                    self.net.stop()
                    import sys
                    sys.exit(0)
                    
                elif data == "GET_HOSTS":
                    host_names = " ".join([host.name for host in self.net.hosts])
                    conn.send(host_names.encode())
                    
                elif data == "GET_HOST_MACS":
                    # Get MAC addresses of all hosts
                    host_macs = {}
                    for host in self.net.hosts:
                        # Get MAC address of the host's interface
                        result = host.cmd('cat /sys/class/net/*/address').strip()
                        # Take the first MAC address (usually the main interface)
                        if result:
                            mac_addresses = result.split('\n')
                            # Filter out loopback MAC (00:00:00:00:00:00)
                            for mac in mac_addresses:
                                if mac != '00:00:00:00:00:00' and ':' in mac:
                                    host_macs[host.name] = mac.strip()
                                    break
                    
                    response = f"HOST_MACS {json.dumps(host_macs)}"
                    conn.send(response.encode())

            except Exception as e:
                print(f"Error handling command: {e}")
                break
        conn.close()

    def start_container(self, host_name, container_name, image_path):
        host = self.net.get(host_name)
        if host:
            print(f"Starting container {container_name} on host {host_name}")
            
            # Load the Docker image
            load_result = host.cmd(f'docker load -i {image_path}')
            print(f"Docker load result: {load_result}")
            
            # Start the container with network host mode for better integration
            run_result = host.cmd(f'docker run -d --name {container_name}_{host_name} --net=host {container_name}')
            print(f"Docker run result: {run_result}")
            
            # Optionally, you can also assign a specific IP to the container
            # This would require more advanced networking setup

    def stop_container(self, host_name, container_name):
        host = self.net.get(host_name)
        if host:
            print(f"Stopping container {container_name} on host {host_name}")
            stop_result = host.cmd(f'docker rm -f {container_name}_{host_name}')
            print(f"Container stop result: {stop_result}")

    def stop_all_containers(self):
        print("Stopping all containers")
        for host in self.net.hosts:
            result = host.cmd('docker rm -f $(docker ps -a -q) 2>/dev/null || true')
            print(f"Stopped containers on {host.name}: {result}")

def main(num_switches, num_hosts, links_prob):
    # Create network
    print(f"Starting with parameters: switches={num_switches}, hosts={num_hosts}, link_prob={links_prob}")
    topo = RandomTopo()
    topo.build(num_switches, num_hosts, links_prob)
    net = Mininet(topo=topo, controller=RemoteController('c1', ip='127.0.0.1', port=6633))
    print("Starting Mininet network")
    net.start()

    # Wait for network to stabilize
    print("Waiting for network to stabilize...")
    net.waitConnected()
    
    # Ensure all hosts can reach each other initially (for ARP resolution)
    print("Performing initial connectivity test...")
    net.pingAll()

    print("Starting socket server")
    server = NetworkServer(net)
    
    # Start a thread to handle incoming connections
    def handle_connections():
        conn, addr = server.sock.accept()
        print(f"Connection established with {addr}")
        threading.Thread(target=server.handle_commands, args=(conn,)).start()
    
    # Start the connection handler thread
    threading.Thread(target=handle_connections).start()
    
    print("Starting Mininet CLI")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(1)
    
    num_switches = int(sys.argv[1])
    num_hosts = int(sys.argv[2])
    links_prob = float(sys.argv[3])
    main(num_switches, num_hosts, links_prob)