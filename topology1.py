from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.cli import CLI
from mininet.link import TCLink

#create network
net = Mininet(controller=Controller, switch=OVSSwitch)

#to add ryo controller at a second date
#net.addController("c0", ip="127.0.0.1", port=6653)

# OVSSWTICH
s1 = net.addSwitch("s1", protocols="OpenFlow13")
s2 = net.addSwitch("s2", protocols="OpenFlow13")
s3 = net.addSwitch("s3", protocols="OpenFlow13")
s4 = net.addSwitch("s4", protocols="OpenFlow13")
s5 = net.addSwitch("s5", protocols="OpenFlow13")

#hosts 
#to later change to docker host
#h1 = net.addHost("h1",cls=DockerHost,ip="10.0.0.1")
h1 = net.addHost("h1", ip="10.0.0.1")
h2 = net.addHost("h2", ip="10.0.0.2")
h3 = net.addHost("h3", ip="10.0.0.3")
h4 = net.addHost("h4", ip="10.0.0.4")
h5 = net.addHost("h5", ip="10.0.0.5")
h6 = net.addHost("h6", ip="10.0.0.6")
h7 = net.addHost("h7", ip="10.0.0.7")


#LINKS
net.addLink(h1, s1)
net.addLink(h2, s2)
net.addLink(h3,s2)
net.addLink(h4, s3)
net.addLink(h5, s4)
net.addLink(h6, s4)
net.addLink(h7, s5)

net.addLink(s1,s2)
net.addLink(s2,s3)
net.addLink(s3,s4)
net.addLink(s4,s5)
net.addLink(s5,s1)


net.start()

net.pingAll()

CLI(net)

net.stop()
