from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller,RemoteController
from mininet.cli import CLI
import docker

c1=RemoteController('c1', ip='127.0.0.1', port = 6633)
client = docker.from_env()

def stop_containers(host):
    host.cmd('docker stop $(docker ps -q)')
#Ferma tutti i container???
def clean_containers(host):
    host.cmd('docker rm -f $(docker ps -a -q)')  
# Rimuove tutti i container


class SimpleTopo(Topo):
    def build(self):
        # hosts
        host1 = self.addHost('h1')
        host2 = self.addHost('h2')
        host3 = self.addHost('h3')
        host4 = self.addHost('h4')
        host5 = self.addHost('h5')
        host6 = self.addHost('h6')
        host7 = self.addHost('h7')
        # switches
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')
        switch4 = self.addSwitch('s4')
        switch5 = self.addSwitch('s5')

        # links between hosts
        self.addLink(host1, switch1)
        self.addLink(host2, switch2)
        self.addLink(host3, switch2)
        self.addLink(host4, switch3)
        self.addLink(host5, switch4)
        self.addLink(host6, switch4)
        self.addLink(host7, switch5)
       
        # links between switches
        self.addLink(switch1, switch2)
        self.addLink(switch2, switch3)
        self.addLink(switch3, switch4)
        self.addLink(switch4, switch5)
#        self.addLink(switch5, switch2)
        
# creation of the netwwork
if __name__ == '__main__':
    topo = SimpleTopo()
    net = Mininet( topo=topo, build=False )
    net.addController(c1)
    net.build()
    net.start()

    host1 = net.get('h1')
#    host1.cmd('docker run -d --name container1_h1 --net=host ubuntu bash -c "while true; do echo Ciao da h1-container1; sleep 2; done"')

    docker_images = client.images.list()
    image_id = ''
    for image in docker_images:
        if image.tags[0] == 'postgres:latest':
                image_id = image.id
                print(f"image id: {image.id}")
    docker_command = f"docker run -d --name mockDB --net-host {image_id}"
    host1.cmd(docker_command)

    CLI(net)
    # stop once exit from cli
    clean_containers(host1)
    net.stop()
