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

            # Run the container with host network (no veth needed)
            run_cmd = f'docker run -d --name {container_full_name} --rm --network host {container_name}'
            result = host.cmd(run_cmd)
            print(f"Docker run result: {result}")

            # Track running container
            if host_name not in self.running_containers:
                self.running_containers[host_name] = set()
            self.running_containers[host_name].add(container_name)

            # Verify container is running
            check_cmd = f'docker ps --filter name={container_full_name} --format "table {{{{.Names}}}}\t{{{{.Status}}}}"'
            status = host.cmd(check_cmd)
            print(f"Container status: {status}")

    def stop_container(self, host_name, container_name):
        host = self.net.get(host_name)
        host.cmd(f'docker rm -f {container_name}_{host_name}')

    def stop_all_containers(self):
        print("Stopping all Docker containers on all hosts")
        for host in self.net.hosts:
            host.cmd('docker rm -f $(docker ps -aq)')