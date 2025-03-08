import sys
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox, QGridLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QObject
from network import NetworkManager

network_running = False
topology_generated = False
nm = NetworkManager()
hosts={}
switches={}

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("CONTAINER DEPLOYMENT")
        self.setGeometry(100, 100, 600, 400)
        
        gridLayout = QGridLayout()
        gridLayout.setContentsMargins(30, 30, 30, 30)  # Top, Left, Bottom, Right margins
        gridLayout.setVerticalSpacing(2)
        gridLayout.setHorizontalSpacing(2)
        
        # Switches box
        switchesLayout = QHBoxLayout()
        self.switches = QSpinBox()
        switchesLayout.addWidget(QLabel("Switches: "))
        switchesLayout.addWidget(self.switches)
        switchesLayout.setContentsMargins(5, 0, 5, 0)
        
        # Hosts box
        hostsLayout = QHBoxLayout()
        self.hosts = QSpinBox()
        hostsLayout.addWidget(QLabel("Hosts: "))
        hostsLayout.addWidget(self.hosts)
        hostsLayout.setContentsMargins(5, 0, 5, 0)
        
        #HBoxLayouts on grid
        gridLayout.addLayout(switchesLayout, 0, 0)
        gridLayout.addLayout(hostsLayout, 0, 1)
        
        self.generate = QPushButton("Generate Topology")
        gridLayout.addWidget(self.generate, 1, 0, 1, 2, Qt.AlignHCenter)
        
        self.run = QPushButton("RUN")
        self.stop = QPushButton("STOP")
        gridLayout.addWidget(self.run, 2, 0, 1, 1, Qt.AlignHCenter)
        gridLayout.addWidget(self.stop, 2, 1, 1, 1, Qt.AlignHCenter)
        
        #self.open_cli = QPushButton("Open Mininet CLI")
        #gridLayout.addWidget(self.open_cli, 3, 0, 1, 2, Qt.AlignHCenter)
        
        self.run.setFixedSize(100, 35)
        self.stop.setFixedSize(100, 35)
        self.generate.setFixedSize(150, 50)
        
        self.run.setEnabled(False)
        self.stop.setEnabled(False)
        
        # Connect signals
        self.run.clicked.connect(self.run_clicked)
        self.stop.clicked.connect(self.stop_clicked)
        self.generate.clicked.connect(self.generate_clicked)
        #self.open_cli.clicked.connect(self.open_cli_clicked)

        self.setLayout(gridLayout)
    
    def run_clicked(self):
        global network_running
        print("RUN")
        nm.build_network()
        nm.start_network()
        network_running = True
        self.run.setEnabled(False)
        self.stop.setEnabled(True)
    
    def stop_clicked(self):
        global network_running
        print("STOP")
        nm.stop_network()
        network_running = False
        self.stop.setEnabled(False)
        self.run.setEnabled(True)
        self.generate.setEnabled(True)
    
    def generate_clicked(self):
        global topology_generated
        print("GENERATE")
        desired_switches = self.switches.value()
        desired_hosts = self.hosts.value()  
        hosts,switches=nm.generate_topology(desired_switches,desired_hosts,0.5)
        topology_generated = True
        self.run.setEnabled(True)
        self.stop.setEnabled(False)
        self.generate.setEnabled(False) 

    #def open_cli_clicked(self):
    #    print("Opening Mininet CLI")
    #    nm.open_cli()
    
    def closeEvent(self, event):
        """Handle window close event"""
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