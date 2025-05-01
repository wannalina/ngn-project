import socket
import threading
import json
import sys
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel

setLogLevel('info')

class CustomTopo(Topo):
    def build(self, num_switches, num_hosts, links_prob):
        switches = [self.addSwitch(f's{i+1}') for i in range(num_switches)]
        hosts = [self.addHost(f'h{i+1}') for i in range(num_hosts)]

        # Connect hosts to random switches
        for i, h in enumerate(hosts):
            self.addLink(h, switches[i % num_switches])

        # Randomly connect switches
        for i in range(num_switches):
            for j in range(i+1, num_switches):
                import random
                if random.random() < float(links_prob):
                    self.addLink(switches[i], switches[j])

def start_socket_server(net):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 9999))
    server_socket.listen(5)
    print("Socket server listening on port 9999")

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(conn, net)).start()

def handle_client(conn, net):
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            print("Received:", data)

            if data == "GET_HOSTS":
                host_names = [h.name for h in net.hosts]
                conn.send(" ".join(host_names).encode())

            elif data.startswith("GET_HOST_DETAILS"):
                try:
                    _, host_name = data.split()
                    host = net.get(host_name)
                    intf = host.defaultIntf()
                    link = host.connectionsTo(None)[0] #intf.link
                    switch = link[1].node if link[0].node == host else link[0].node  # Identify switch
                    switch_intf = link[1] if link[0].node == host else link[0]        # Switch interface
                    #port = link.intf2 if link.intf1 == intf else link.intf1
                    #switch = port.node
                    port_number = switch.ports[switch_intf].port_no
                    dpid = switch.dpid
                    
                    print("port number:", port_number)
                    #port_number = switch.ports[intf].port_no

                    # find the correct port number on the switch
                    #port_number = None
                    #for p in switch.ports.values():
                    #    if p == port:
                    #        port_number = p.port_no
                    #        break

                    response = {
                        "host": host.name,
                        "host_mac": host.MAC(),
                        "dpid": dpid,
                        "port": port_number
                    }
                    conn.send(json.dumps(response).encode())
                except Exception as e:
                    conn.send(f"ERROR: {e}".encode())

            elif data.startswith("START_CONTAINER"):
                # Placeholder logic for container start
                conn.send("ACK: container started".encode())

            elif data.startswith("STOP_CONTAINER"):
                conn.send("ACK: container stopped".encode())

            elif data == "STOP_ALL":
                conn.send("ACK: all containers stopped".encode())

            elif data == "SHUTDOWN":
                print("Shutdown command received.")
                conn.close()
                net.stop()
                import os
                os._exit(0)

            else:
                conn.send("UNKNOWN_COMMAND".encode())
    except Exception as e:
        print(f"Client handler error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 topology_generator.py <num_switches> <num_hosts> <links_prob>")
        sys.exit(1)

    num_switches = int(sys.argv[1])
    num_hosts = int(sys.argv[2])
    links_prob = float(sys.argv[3])

    topo = CustomTopo(num_switches=num_switches, num_hosts=num_hosts, links_prob=links_prob)
    net = Mininet(topo=topo, controller=RemoteController, link=TCLink, switch=OVSSwitch, autoSetMacs=True)
    net.start()

    threading.Thread(target=start_socket_server, args=(net,), daemon=True).start()

    print("Topology started. Use SHUTDOWN to stop.")
    while True:
        pass  # Keep main thread alive
