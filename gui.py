import sys
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox, QGridLayout, QLabel, QPushButton, QHBoxLayout, QDoubleSpinBox,QGroupBox,QVBoxLayout,QComboBox,QScrollArea
from PyQt5.QtCore import Qt, QObject
from network import NetworkManager

network_running = False
topology_generated = False
nm = NetworkManager()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("CONTAINER DEPLOYMENT")
        self.setGeometry(100, 100, 600, 650)
        
        mainLayout=QVBoxLayout();
        #TOPOLOGY AREA
        topoGroupBox=QGroupBox("TOPOLOGY")
        topoLayout = QGridLayout()
        topoLayout.setContentsMargins(30, 30, 30, 30)  # Top, Left, Bottom, Right margins
        topoLayout.setVerticalSpacing(22)
        topoLayout.setHorizontalSpacing(2)
        
        # Switches box
        switchesLayout = QHBoxLayout()
        self.switchesBox = QSpinBox()
        self.switchesBox.setRange(2,10)
        switchesLayout.addWidget(QLabel("Switches: "))
        switchesLayout.addWidget(self.switchesBox)
        switchesLayout.setContentsMargins(5, 0, 5, 0)
        
        # Hosts box
        hostsLayout = QHBoxLayout()
        self.hostsBox = QSpinBox()
        self.hostsBox.setRange(3,30)
        hostsLayout.addWidget(QLabel("Hosts: "))
        hostsLayout.addWidget(self.hostsBox)
        hostsLayout.setContentsMargins(5, 0, 5, 0)
        
        # Link probability box
        linkProbLayout = QHBoxLayout()
        self.linkProbBox = QDoubleSpinBox()
        self.linkProbBox.setRange(0.1, 1.0)
        self.linkProbBox.setSingleStep(0.1)
        self.linkProbBox.setValue(0.5)
        linkProbLayout.addWidget(QLabel("Link prob: "))
        linkProbLayout.addWidget(self.linkProbBox)
        linkProbLayout.setContentsMargins(5, 0, 5, 0)
        
        #HBoxLayouts on grid
        topoLayout.addLayout(switchesLayout, 0, 0)
        topoLayout.addLayout(hostsLayout, 0, 1)
        topoLayout.addLayout(linkProbLayout, 0, 2)
        
        self.generate = QPushButton("Generate Topology")
        topoLayout.addWidget(self.generate, 1, 0, 1, 3, Qt.AlignHCenter)
        
        self.run = QPushButton("RUN")
        self.stop = QPushButton("STOP")
        topoLayout.addWidget(self.run, 2, 0, 1, 1, Qt.AlignRight)
        topoLayout.addWidget(self.stop, 2, 2, 1, 1, Qt.AlignLeft)
        topoGroupBox.setLayout(topoLayout)
        mainLayout.addWidget(topoGroupBox)
        ##TOPOLOGY FINISHED

        #NET PARAMETERS SECTION TO BE ADDED HERE MAYBE???
        # FOR EXAMPLE MAX 2H DOCKERS PER HOST

        #DOCKER AREA
        self.containerGroupBox = QGroupBox("DOCKERS")
        self.containerGroupBox.setEnabled(False)
        containerLayout = QGridLayout()
        
        dockerHostsLayout=QHBoxLayout()
        dockerHostsLayout.addWidget(QLabel("Hosts: "))
        
        self.hostDropdown = QComboBox()
        dockerHostsLayout.addWidget(self.hostDropdown)

        dockerContainersLayout=QHBoxLayout()
        dockerContainersLayout.addWidget(QLabel("Containers: "))
        self.containerDropdown = QComboBox()
        self.containerDropdown.addItems(["need to make", "container dictonary", "and connnect it somehow"])
        dockerContainersLayout.addWidget(self.containerDropdown)

        self.launchButton = QPushButton("Start container")
        
        containerLayout.addLayout(dockerHostsLayout,0,0)
        containerLayout.addLayout(dockerContainersLayout,0,1)
        containerLayout.addWidget(self.launchButton,0,2)
        
        activeContainersBox=QGroupBox("Active Containers")
        self.activeContainerLayout = QVBoxLayout()
        activeContainersBox.setLayout(self.activeContainerLayout)

        scrollArea=QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(activeContainersBox)
        containerLayout.addWidget(scrollArea,1,0,1,3)
        
        self.stopAllButton = QPushButton("Shut down ALL containers")
        containerLayout.addWidget(self.stopAllButton, 2,1,1,1, Qt.AlignHCenter)
    
        self.containerGroupBox.setLayout(containerLayout)
        mainLayout.addWidget(self.containerGroupBox)
        
        #self.open_cli = QPushButton("Open Mininet CLI")
        #topoLayout.addWidget(self.open_cli, 3, 0, 1, 3, Qt.AlignHCenter)
        
        self.run.setFixedSize(100, 35)
        self.stop.setFixedSize(100, 35)
        self.generate.setFixedSize(130, 45)
        self.launchButton.setFixedSize(130, 30)
        self.stopAllButton.setFixedSize(200, 45)
        
        self.run.setEnabled(False)
        self.stop.setEnabled(False)
        
        # Connect signals
        self.run.clicked.connect(self.run_clicked)
        self.stop.clicked.connect(self.stop_clicked)
        self.generate.clicked.connect(self.generate_clicked)
        #self.open_cli.clicked.connect(self.open_cli_clicked)

        self.setLayout(mainLayout)
    
    def run_clicked(self):
        global network_running
        print("RUN")
        nm.build_network()
        nm.start_network()
        network_running = True
        self.run.setEnabled(False)
        self.stop.setEnabled(True)
        self.containerGroupBox.setEnabled(True)

        self.hostDropdown.clear()
        for host in nm.net.hosts:
            self.hostDropdown.addItem(host.name)

    def stop_clicked(self):
        global network_running
        print("STOP")
        nm.stop_network()
        network_running = False
        self.stop.setEnabled(False)
        self.run.setEnabled(True)
        self.generate.setEnabled(True)
        self.containerGroupBox.setEnabled(False)
    
    def generate_clicked(self):
        global topology_generated
        print("GENERATE")
        desired_switches = self.switchesBox.value()
        desired_hosts = self.hostsBox.value()
        link_probability = self.linkProbBox.value()
        nm.generate_topology(desired_switches,desired_hosts,link_probability)
        topology_generated = True
        self.run.setEnabled(True)
        self.stop.setEnabled(False)
        self.generate.setEnabled(False) 
        
    #def open_cli_clicked(self):
    #    print("Opening Mininet CLI")
    #    nm.open_cli()
    
    def closeEvent(self, event):
        global network_running
        if network_running:
            print("Window closing: Stopping network first")
            nm.stop_network()
            network_running = False
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()