'''
What is this used for? 
1. Creates a TCP socket (socket-based server)
2. Listens to TCP commands (start/stop containers, etc.)
3. Performs actions on Mininet hosts / containers according to commands
'''

# import libraries
import socket
import sys
import json

# class to expose TCP socket interface for managing containers on mininet hosts
class SocketServer:
    def __init__(self, net):
        self.net = net

        # create TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # allow re-use of socket address

        # bind to localhost port 9999; listen to one connection at a time
        self.sock.bind(('localhost', 9999))
        self.sock.listen(1)
        print("Socket server is now listening on localhost:9999")

    # function to handle commands received over the socket
    def handle_commands(self, conn):
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                # start docker container
                if data.startswith("START_CONTAINER"):
                    _, host, container, image = data.split()
                    self.start_container(host, container, image)
                    conn.send("CONTAINER_STARTED".encode())

                # stop docker container
                elif data.startswith("STOP_CONTAINER"):
                    _, host, container = data.split()
                    self.stop_container(host, container)

                # stop all docker containers
                elif data == "STOP_ALL":
                    self.stop_all_containers()

                # shut down mininet network
                elif data == "SHUTDOWN":
                    print("Received shutdown command")
                    self.stop_all_containers()  # stop all docker containers
                    conn.close()                # close socket
                    self.sock.close()           # stop mininet
                    self.net.stop()             # exit gracefully 
                    sys.exit(0)

                # get mininet hosts
                elif data == "GET_HOSTS":
                    host_names = " ".join([host.name for host in self.net.hosts])
                    conn.send(host_names.encode())

                # get information about a specific host
                elif data.startswith("GET_HOST_INFO"):
                    _, host_name = data.split()
                    host = self.net.get(host_name)
                    if host:
                        try:
                            host_mac = host.MAC()
                            print("host", host, host_mac)
                            dpid = host.connectionsTo(host)[0][0].dpid if host.connectionsTo(host) else "unknown"
                            host_info = {
                                "host": host_name,
                                "host_mac": host_mac,
                                "dpid": dpid
                            }
                            response = json.dumps(host_info)
                            conn.send(response.encode())
                        except Exception as e:
                            error_msg = json.dumps({"error": f"Failed to get host info: {e}"})
                            conn.send(error_msg.encode())
                    else:
                        error_msg = json.dumps({"error": f"Host {host_name} not found"})
                        conn.send(error_msg.encode())


            except Exception as e:
                print(f"Error handling command: {e}")
                break
        conn.close()

    # function to start docker container (docker commands)
    def start_container(self, host_name, container_name, image_path):
        host = self.net.get(host_name)
        print("host: ", host)
        if host:
            print(f"Starting container {container_name} on host {host_name}")
            host.cmd(f'docker load -i {image_path}')
            host.cmd(f'docker run -d --name {container_name}_{host_name} --net=host -e CONTAINER_NAME={container_name}_{host_name} {container_name}')

    # function to stop docker container (docker commands)
    def stop_container(self, host_name, container_name):
        host = self.net.get(host_name)
        if host:
            print(f"Stopping container {container_name} on host {host_name}")
            host.cmd(f'docker rm -f {container_name}_{host_name}')

    # function to stop all docker containers (docker commands)
    def stop_all_containers(self):
        print("Stopping all containers")
        for host in self.net.hosts:
            host.cmd('docker rm -f $(docker ps -a -q)')