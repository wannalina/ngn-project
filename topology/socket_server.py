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
                            dpid = host.connectionsTo(host)[0][0].dpid
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
            print(f"Deploying container {container_name} on {host_name}")
            host.cmd(f'docker load -i {image_path}')
            host.cmd(f'docker run -d --name {container_name}_{host_name} --network none --privileged {container_name}')
            pid = host.cmd(f"docker inspect -f '{{{{.State.Pid}}}}' {container_name}_{host_name}").strip()
            host.cmd(f'mkdir -p /var/run/netns')
            host.cmd(f'ln -sf /proc/{pid}/ns/net /var/run/netns/{pid}')
            host.cmd(f'ip link add veth_{pid} type veth peer name veth_{host_name}')
            host.cmd(f'ip link set veth_{pid} netns {pid}')
            host.cmd(f'ip netns exec {pid} ip link set veth_{pid} up')
            host.cmd(f'ip netns exec {pid} ip addr add 10.0.0.{host.IP().split(".")[-1]}/24 dev veth_{pid}')
            host.cmd(f'ip link set veth_{host_name} up')
            host.cmd(f'brctl addif {host.name}-eth0 veth_{host_name}')

    def stop_container(self, host_name, container_name):
        host = self.net.get(host_name)
        pid = host.cmd(f"docker inspect -f '{{{{.State.Pid}}}}' {container_name}_{host_name}").strip()
        host.cmd(f'rm -f /var/run/netns/{pid}')
        host.cmd(f'docker rm -f {container_name}_{host_name}')

    def stop_all_containers(self):
        print("Stopping all Docker containers on all hosts")
        for host in self.net.hosts:
            host.cmd('docker rm -f $(docker ps -aq)')