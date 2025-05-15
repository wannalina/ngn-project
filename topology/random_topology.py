''' 
What is this used for?
1. Defines a custom Mininet topology
2. Connects hosts to switches randomly
3. Adds linear links between switches + Adds extra links for redundancy
'''

# import libraries
from mininet.topo import Topo
import random

# class to define a custom network topology
class RandomTopo(Topo):
    # function to build custom topology
    def build(self, num_switches=0, num_hosts=0, links_prob=0.5):
        switches = []
        hosts = []
        
        # add switches to topology
        for s in range(1, num_switches + 1):
            switch = self.addSwitch(f's{s}')
            switches.append(switch)
        
        # add hosts to topology & connect to randomly chose switches
        for h in range(1, num_hosts + 1):
            host = self.addHost(f'h{h}')
            hosts.append(host)
            # randomly select a switch
            switch = random.choice(switches)
            self.addLink(host, switch)

        # add linear links between consecutive switches
        for i in range(len(switches) - 1):
            self.addLink(switches[i], switches[i + 1])
        
        # add additional links between non-consecutive switches
        for i in range(len(switches)):
            for j in range(i + 2, len(switches)):  # skip close switches
                if random.random() < links_prob:
                    self.addLink(switches[i], switches[j])