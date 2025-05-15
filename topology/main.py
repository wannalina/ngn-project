'''
What is this used for? 
1. Entrypoint of the program (topology generation)
2. Builds topology
3. Starts Mininet
4. Launches socket server
5. Runs CLI
'''

# import libraries
import sys
import threading
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI

# import classes
from random_topology import RandomTopo
from socket_server import SocketServer

# start a thread to handle incoming connections
def handle_connections(server):
    conn, addr = server.sock.accept()  # accept connection
    print(f"Connection established with {addr}")
    threading.Thread(target=server.handle_commands, args=(conn,)).start()

# function to initialize topology with given parameters
def start_topology_with_params(num_switches, num_hosts, links_prob):
    # create mininet network
    print(f"Starting with parameters: switches={num_switches}, hosts={num_hosts}, link_prob={links_prob}")
    topo = RandomTopo()
    topo.build(num_switches, num_hosts, links_prob)
    net = Mininet(topo=topo, controller=RemoteController('c1', ip='127.0.0.1', port=6633))
    print("Starting Mininet network")
    net.start()

    server = SocketServer(net)

    # start connection handler thread
    threading.Thread(target=handle_connections, args=(server,)).start()
    
    print("Starting Mininet CLI")
    CLI(net)
    net.stop()

# initialize program
if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(1)

    # received inputs
    num_switches = int(sys.argv[1])
    num_hosts = int(sys.argv[2])
    links_prob = float(sys.argv[3])
    start_topology_with_params(num_switches, num_hosts, links_prob)