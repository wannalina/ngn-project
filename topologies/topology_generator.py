from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
import random

class RandomTopo(Topo):
    def build(self, num_switches=5, num_hosts=7, links_prob=0.4):
        
        # Add switches
        switches = []
        for s in range(1, num_switches + 1):
            switch = self.addSwitch(f's{s}')
            switches.append(switch)
        
        # Add hosts and connect to switches
        hosts = []
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
        
        return hosts, switches

# creation of the netwwork
if __name__ == '__main__':
    topo = RandomTopo(5,10,0.4)
    c1=RemoteController('c1', ip='127.0.0.1', port = 6633)
    net = Mininet( topo=topo, build=False )
    net.addController(c1)
    net.build()
    net.start()
    
    CLI(net)
    # stop once exit from cli
    net.stop()