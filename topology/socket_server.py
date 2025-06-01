'''
What is this used for? 
1. Creates a TCP socket (socket-based server)
2. Listens to TCP commands (start/stop containers, etc.)
3. Performs actions on Mininet hosts / containers according to commands
'''

import socket
import sys
import json

class SocketServer:
    def __init__(self, net):
        self.running_containers = {}
        self.net = net
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('localhost', 9999))
        self.sock.listen(1)
        print("Socket server listening on localhost:9999")

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


                elif data == "STOP_ALL":
                    self.stop_all_containers()

                elif data == "SHUTDOWN":
                    print("Shutdown signal received")
                    self.stop_all_containers()
                    conn.close()
                    self.sock.close()
                    self.net.stop()
                    sys.exit(0)

                elif data == "GET_HOSTS":
                    host_names = " ".join([host.name for host in self.net.hosts])
                    conn.send(host_names.encode())

                elif data.startswith("GET_HOST_INFO"):
                    _, host_name = data.split()
                    host = self.net.get(host_name)
                    if host:
                        try:
                            host_mac = host.MAC()

                            # get the first switch the host is connected to
                            if host.intf().link:
                                dpid = host.intf().link.intf2.node.dpid
                            else:
                                dpid = 0

                            host_info = {
                                "host": host_name,
                                "host_mac": host_mac,
                                "dpid": dpid
                            }
                            response = json.dumps(host_info)
                            conn.send(response.encode())
                        except Exception as e:
                            error_msg = json.dumps({"error": f"Host info error: {e}"})
                            conn.send(error_msg.encode())
                    else:
                        conn.send(json.dumps({"error": "Host not found"}).encode())

            except Exception as e:
                print(f"Socket command error: {e}")
                break
        conn.close()

    def start_container(self, host_name, container_name, image_path):
        host = self.net.get(host_name)
        if host:
            print(f"Starting container {container_name} on host {host_name}")

            # Load the Docker image
            load_result = host.cmd(f'docker load -i {image_path}')
            print(f"Docker load result: {load_result}")

            container_full_name = f"{container_name}_{host_name}"

            # Remove any existing container with the same name
            host.cmd(f'docker rm -f {container_full_name} 2>/dev/null')

            # Run the container with no network so we can connect manually
            run_cmd = f'docker run -d --name {container_full_name} --network=none {container_name}'
            result = host.cmd(run_cmd)
            print(f"Docker run result: {result}")

            # Setup veth connection to the Mininet host
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
        pid = host.cmd(f"docker inspect -f '{{{{.State.Pid}}}}' {container_name}_{host_name}").strip()
        host.cmd(f'rm -f /var/run/netns/{pid}')
        host.cmd(f'docker rm -f {container_name}_{host_name}')

    def stop_all_containers(self):
        print("Stopping all Docker containers on all hosts")
        for host in self.net.hosts:
            host.cmd('docker rm -f $(docker ps -aq)')