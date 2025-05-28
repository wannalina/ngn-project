import subprocess
import threading
import socket
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
import random
import sys
import time

class RandomTopo(Topo):
    def build(self, num_switches=0, num_hosts=0, links_prob=0.5):
        switches = []
        hosts = []
        #Add switches
        for s in range(1, num_switches + 1):
            switch = self.addSwitch(f's{s}')
            switches.append(switch)
        
        #Add hosts and connect to switches
        for h in range(1, num_hosts + 1):
            host = self.addHost(f'h{h}')
            hosts.append(host)
            # Randomly select 1 switch
            switch = random.choice(switches)
            self.addLink(host, switch)

        #Linear connectivity
        for i in range(len(switches) - 1):
            self.addLink(switches[i], switches[i + 1])
        
        #Random extra connectivity
        for i in range(len(switches)):
            for j in range(i + 2, len(switches)):  # skip close switches
                if random.random() < links_prob:
                    self.addLink(switches[i], switches[j])

class NetworkServer:
    def __init__(self, net):
        self.net = net
        self.running_containers = {}  # Track running containers
        #print("Creating socket")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #print("Binding socket to localhost:9999")
        self.sock.bind(('localhost', 9999))
        #print("Socket bound successfully. Listening for connections")
        self.sock.listen(1)
        print("Socket server is now listening on localhost:9999")

    def handle_commands(self, conn):
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

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
                elif data == "LIST_CONTAINERS":
                    # New command to list running containers
                    container_info = []
                    for host_name, containers in self.running_containers.items():
                        for container_name in containers:
                            container_info.append(f"{host_name}:{container_name}")
                    response = " ".join(container_info) if container_info else "NO_CONTAINERS"
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
            
            # Get the host's network namespace PID
            host_pid = host.cmd('echo $$').strip()
            
            # Method 1: Use docker run with network namespace sharing
            container_full_name = f"{container_name}_{host_name}"
            
            # First, try to remove any existing container with the same name
            host.cmd(f'docker rm -f {container_full_name} 2>/dev/null')
            
            # Start container in the host's network namespace
            # Option A: Share network namespace with a process running in the mininet host
            run_cmd = f'docker run -d --name {container_full_name} --network container:$(docker run -d --rm --net=none alpine sleep 3600) {container_name}'
            
            # Option B: Better approach - use nsenter to run docker in the correct namespace
            # This requires the container to be started from within the mininet host's context
            run_cmd = f'docker run -d --name {container_full_name} --network=none {container_name}'
            
            result = host.cmd(run_cmd)
            print(f"Docker run result: {result}")
            
            # Configure networking manually to integrate with Mininet
            # Get container PID
            container_id = result.strip()
            if container_id:
                # Move container to host's network namespace
                host_netns_cmd = f'docker exec {container_full_name} ip link set dev eth0 netns 1 2>/dev/null || echo "No eth0 to move"'
                host.cmd(host_netns_cmd)
                
                # Alternative: Create veth pair and connect container to host
                self._setup_container_networking(host, container_full_name, host_name)
            
            # Track running container
            if host_name not in self.running_containers:
                self.running_containers[host_name] = set()
            self.running_containers[host_name].add(container_name)
            
            # Verify container is running
            check_cmd = f'docker ps --filter name={container_full_name} --format "table {{{{.Names}}}}\t{{{{.Status}}}}"'
            status = host.cmd(check_cmd)
            print(f"Container status: {status}")

    def _setup_container_networking(self, host, container_name, host_name):
        """Setup networking between container and mininet host"""
        try:
            # Get container PID
            pid_cmd = f'docker inspect -f "{{{{.State.Pid}}}}" {container_name}'
            container_pid = host.cmd(pid_cmd).strip()
            
            if container_pid and container_pid != "0":
                # Create veth pair
                veth_host = f"veth-{host_name}"
                veth_container = f"veth-c-{host_name}"
                
                # Create veth pair
                host.cmd(f'ip link add {veth_host} type veth peer name {veth_container}')
                
                # Move container end to container namespace
                host.cmd(f'ip link set {veth_container} netns {container_pid}')
                
                # Configure host end
                host.cmd(f'ip link set {veth_host} up')
                
                # Configure container end (run in container's namespace)
                host.cmd(f'nsenter -t {container_pid} -n ip link set {veth_container} name eth0')
                host.cmd(f'nsenter -t {container_pid} -n ip link set eth0 up')
                
                # Assign IP to container (simple scheme: 10.0.hostnum.2)
                host_num = host_name.replace('h', '')
                container_ip = f"10.0.{host_num}.2/24"
                host.cmd(f'nsenter -t {container_pid} -n ip addr add {container_ip} dev eth0')
                
                print(f"Configured networking for container {container_name}: {container_ip}")
        
        except Exception as e:
            print(f"Error setting up container networking: {e}")

    def stop_container(self, host_name, container_name):
        host = self.net.get(host_name)
        if host:
            print(f"Stopping container {container_name} on host {host_name}")
            container_full_name = f"{container_name}_{host_name}"
            
            # Clean up veth interfaces
            veth_host = f"veth-{host_name}"
            host.cmd(f'ip link delete {veth_host} 2>/dev/null || true')
            
            # Stop and remove container
            result = host.cmd(f'docker rm -f {container_full_name}')
            print(f"Container stop result: {result}")
            
            # Update tracking
            if host_name in self.running_containers:
                self.running_containers[host_name].discard(container_name)
                if not self.running_containers[host_name]:
                    del self.running_containers[host_name]

    def stop_all_containers(self):
        print("Stopping all containers")
        for host in self.net.hosts:
            # Clean up all veth interfaces for this host
            host_name = host.name
            veth_host = f"veth-{host_name}"
            host.cmd(f'ip link delete {veth_host} 2>/dev/null || true')
            
            # Stop all containers
            host.cmd('docker rm -f $(docker ps -a -q) 2>/dev/null || true')
        
        # Clear tracking
        self.running_containers.clear()

    def get_container_status(self):
        """Debug method to check container status"""
        for host in self.net.hosts:
            print(f"\n=== Host {host.name} ===")
            containers = host.cmd('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
            print(f"Containers: {containers}")
            
            network = host.cmd('ip addr show')
            print(f"Network interfaces: {network}")

def main(num_switches, num_hosts, links_prob):
    # Create network
    print(f"Starting with parameters: switches={num_switches}, hosts={num_hosts}, link_prob={links_prob}")
    topo = RandomTopo()
    topo.build(num_switches, num_hosts, links_prob)
    net = Mininet(topo=topo, controller=RemoteController('c1', ip='127.0.0.1', port=6633))
    print("Starting Mininet network")
    net.start()

    # Give network time to stabilize
    time.sleep(2)

    #print("Starting socket server")
    server = NetworkServer(net)
    
    # Start a thread to handle incoming connections
    def handle_connections():
        #print("Waiting for a connection")
        conn, addr = server.sock.accept()
        print(f"Connection established with {addr}")
        threading.Thread(target=server.handle_connections, args=(conn,)).start()
    
    # Start the connection handler thread
    threading.Thread(target=handle_connections).start()
    
    print("Starting Mininet CLI")
    print("You can use 'py server.get_container_status()' to debug container status")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(1)
    
    num_switches = int(sys.argv[1])
    num_hosts = int(sys.argv[2])
    links_prob = float(sys.argv[3])
    main(num_switches, num_hosts, links_prob)