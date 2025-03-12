import sys,os
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox, QGridLayout, QLabel, QPushButton, QHBoxLayout, QDoubleSpinBox,QGroupBox,QVBoxLayout,QComboBox,QScrollArea,QFrame, QDialog, QListWidget, QCheckBox, QListWidgetItem
from PyQt5.QtCore import Qt, QObject
from network import NetworkManager
import random

network_running = False
topology_generated = False
nm = NetworkManager()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.availableContainers={} #name (key) + directory
        self.runningContainers={} #container_id (key) + host + container type 
        self.containerDependencies={}  
        self.hostContainerCounts = {}  #container per host, hostname(key) + int
        
    def initUI(self):
        self.setWindowTitle("CONTAINER DEPLOYMENT")
        self.setGeometry(100, 100, 550, 650)
        self.setFixedSize(550,850)
        
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
        
        # Max Containers per Host
        maxContainersLayout = QHBoxLayout()
        self.maxContainersBox = QSpinBox()
        self.maxContainersBox.setRange(1,3)
        self.maxContainersBox.setValue(2)
        maxContainersLayout.addWidget(QLabel("Max containers per host: "))
        maxContainersLayout.addWidget(self.maxContainersBox)
        maxContainersLayout.setContentsMargins(5,0,5,0)
        
        #HBoxLayouts on grid
        topoLayout.addLayout(switchesLayout, 0, 0)
        topoLayout.addLayout(hostsLayout, 0, 1)
        topoLayout.addLayout(linkProbLayout, 0, 2)
        topoLayout.addLayout(maxContainersLayout, 1, 0, 1, 3)
        
        self.generate = QPushButton("Generate Topology")
        topoLayout.addWidget(self.generate, 2, 0, 1, 3, Qt.AlignHCenter)
        
        self.run = QPushButton("RUN")
        self.stop = QPushButton("STOP")
        topoLayout.addWidget(self.run, 3, 0, 1, 1, Qt.AlignRight)
        topoLayout.addWidget(self.stop, 3, 2, 1, 1, Qt.AlignLeft)
        topoGroupBox.setLayout(topoLayout)
        mainLayout.addWidget(topoGroupBox)
        ##TOPOLOGY FINISHED
        #DOCKER AREA
        self.containerGroupBox = QGroupBox("DOCKERS")
        containerLayout = QGridLayout()

        self.dependencyButton = QPushButton("Select Dependencies")
        self.dependencyButton.clicked.connect(self.openDependencyDialog)
        containerLayout.addWidget(self.dependencyButton, 0, 0, 1, 3, Qt.AlignHCenter)
        
        dockerHostsLayout=QHBoxLayout()
        dockerHostsLayout.addWidget(QLabel("Hosts: "))
        self.hostDropdown = QComboBox()
        self.hostDropdown.currentTextChanged.connect(self.updateLaunchButton)
        dockerHostsLayout.addWidget(self.hostDropdown)

        dockerContainersLayout=QHBoxLayout()
        dockerContainersLayout.addWidget(QLabel("Containers: "))
        self.containerDropdown = QComboBox()
        self.containerDropdown.currentTextChanged.connect(self.updateLaunchButton)
        dockerContainersLayout.addWidget(self.containerDropdown)

        self.launchButton = QPushButton("Start container")
        
        containerLayout.addLayout(dockerHostsLayout, 1, 0)
        containerLayout.addLayout(dockerContainersLayout, 1, 1)
        containerLayout.addWidget(self.launchButton,1, 2)
        
        # Auto Deploy Button
        self.autoDeployButton = QPushButton("Auto Deploy All Containers")
        containerLayout.addWidget(self.autoDeployButton, 2, 0, 1, 3, Qt.AlignHCenter)
        
        activeContainersBox=QGroupBox("Active Containers")
        self.activeContainerLayout = QVBoxLayout()
        activeContainersBox.setLayout(self.activeContainerLayout)

        scrollArea=QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(activeContainersBox)
        containerLayout.addWidget(scrollArea, 3, 0, 1, 3)
        
        self.stopAllButton = QPushButton("Shut down ALL containers")
        containerLayout.addWidget(self.stopAllButton, 4, 0, 1, 3, Qt.AlignHCenter)
    
        self.containerGroupBox.setLayout(containerLayout)
        mainLayout.addWidget(self.containerGroupBox)

        self.updateEnables()
        
        self.run.setFixedSize(100, 35)
        self.stop.setFixedSize(100, 35)
        self.generate.setFixedSize(130, 45)
        self.launchButton.setFixedSize(130, 30)
        self.dependencyButton.setFixedSize(200, 35)
        self.autoDeployButton.setFixedSize(200, 45)
        self.stopAllButton.setFixedSize(200, 45)
        
        # Connect signals
        self.run.clicked.connect(self.run_clicked)
        self.stop.clicked.connect(self.stop_clicked)
        self.generate.clicked.connect(self.generate_clicked)
        self.launchButton.clicked.connect(self.startContainer)
        self.stopAllButton.clicked.connect(self.stopAllContainers)
        self.autoDeployButton.clicked.connect(self.autoDeployContainers)

        self.setLayout(mainLayout)
    
    def run_clicked(self):
        global network_running
        print("RUN")
        nm.build_network()
        nm.start_network()
        network_running = True
        self.updateEnables()
    
        self.containerDependencies={}
        self.hostDropdown.clear()
        for host in nm.net.hosts:
            self.hostDropdown.addItem(host.name)
            self.hostContainerCounts[host.name] = 0
        self.containerDropdown.clear()
        self.findContainers()
        self.updateContainerDropdown()

    def stop_clicked(self):
        global network_running
        print("STOP")
        self.stopAllContainers()
        nm.stop_network()
        network_running = False
        
        self.updateEnables()
    
    def generate_clicked(self):
        global topology_generated
        print("GENERATE")
        desired_switches = self.switchesBox.value()
        desired_hosts = self.hostsBox.value()
        link_probability = self.linkProbBox.value()
        nm.generate_topology(desired_switches,desired_hosts,link_probability)
        topology_generated = True
        self.updateEnables()
        
    #def open_cli_clicked(self):
    #    print("Opening Mininet CLI")
    #    nm.open_cli()
    
    def closeEvent(self, event):
        global network_running
        if network_running:
            print("Window closing: Stopping network first")
            self.stopAllContainers()
            nm.stop_network()
            network_running = False
        event.accept()

    def updateEnables(self):
        self.containerGroupBox.setEnabled(network_running and topology_generated)
        self.run.setEnabled(topology_generated and not network_running)
        self.stop.setEnabled(network_running and topology_generated)
        self.generate.setEnabled(not network_running)
        self.linkProbBox.setEnabled(not network_running)
        self.hostsBox.setEnabled(not network_running)
        self.switchesBox.setEnabled(not network_running)
        self.maxContainersBox.setEnabled(not network_running)
    
    def updateLaunchButton(self):
        if self.containerGroupBox.isEnabled():
            container = self.containerDropdown.currentText()
            host = self.hostDropdown.currentText()
            max_containers = self.maxContainersBox.value()

            at_limit = False
            if host:
                current_count = self.hostContainerCounts.get(host,0) #method sometimes is called before current is initliazied as 0
                at_limit = current_count >= max_containers
            #self.dependencyButton.setEnabled(bool(container))
            self.launchButton.setEnabled(bool(container) and not at_limit)

    def findContainers(self):
        self.availableContainers = {}
        current_dir = os.path.dirname(os.path.abspath(__file__)) #this is where current file is located
        apps_dir = os.path.join(current_dir, "apps") #path to apps
        for folder in os.listdir(apps_dir):
            folder_path = os.path.join(apps_dir, folder)
            if os.path.isdir(folder_path):
                tar_files = [f for f in os.listdir(folder_path) if f.endswith(".tar")]
                if tar_files:
                    self.availableContainers[folder] = os.path.relpath(os.path.join(folder_path, tar_files[0]), current_dir)
                else:
                    self.availableContainers[folder] = None
    
    def updateContainerDropdown(self):
        self.containerDropdown.clear()
        # Add only containers that are not currently running
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                self.containerDropdown.addItem(container)
        #self.containerDependencies={}  
    
    def startContainer(self):
        host = self.hostDropdown.currentText()
        container = self.containerDropdown.currentText()
        if not container: 
            return
        nm.start_container(host, container, self.availableContainers[container])
        container_id = f"{container}_{host}"
        self.runningContainers[container_id] = {"host": host, "container": container}
        self.hostContainerCounts[host] = self.hostContainerCounts.get(host) + 1
        
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.updateLaunchButton()
        self.updateMonitor()
        self.checkAutoDeploy()

    def stopAllContainers(self):
        nm.stop_all_containers()   
        self.cleanMonitor()
        self.runningContainers = {}
        #self.containerDependencies = {}
        self.hostContainerCounts = {host: 0 for host in self.hostContainerCounts}
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.updateLaunchButton()
        self.checkAutoDeploy()
    
    def updateMonitor(self):
        self.cleanMonitor()
        for container_id, data in self.runningContainers.items():
              container_frame = QFrame()
              container_frame.setFrameShape(QFrame.StyledPanel)
              container_layout = QHBoxLayout()
              container_frame.setFixedSize(478, 60)
              #container_frame.setFrameRect(QRect(10,10,300,300))
              label = QLabel(f"Host: {data['host']} | Container: {data['container']}")
              stop_button = QPushButton("KILL")
              stop_button.setFixedSize(70, 25)
              stop_button.clicked.connect(lambda checked=False, host=data['host'], container=data['container']: self.stop_container(host, container))

              container_layout.addWidget(label)
              container_layout.addWidget(stop_button)
              container_frame.setLayout(container_layout)
              self.activeContainerLayout.addWidget(container_frame)
    
    def cleanMonitor(self):
        while self.activeContainerLayout.count():
            item = self.activeContainerLayout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def stop_container(self, host, container):
        nm.stop_container(host, container)
        container_id = f"{container}_{host}"
        if container_id in self.runningContainers:
            #if container in self.containerDependencies:
            #    del self.containerDependencies[container]
            del self.runningContainers[container_id]
            self.hostContainerCounts[host] = self.hostContainerCounts.get(host) - 1
            self.updateContainerDropdown()
            self.updateHostDropdown()
            self.updateMonitor()
            self.updateLaunchButton()
            self.checkAutoDeploy()
    
    def openDependencyDialog(self):
        print(self.containerDependencies)
        container_select_dialog = QDialog(self)
        container_select_dialog.setWindowTitle("Containers")
        container_select_dialog.setMinimumWidth(300)
        select_layout = QVBoxLayout()
        
        select_label = QLabel("Select a container to set dependencies:")
        select_layout.addWidget(select_label)
        
        container_list = QListWidget()
       #FETCH ALL CONTAINERS
        all_containers = set(self.availableContainers.keys())
        for container in all_containers:
            container_list.addItem(container)
            
        select_layout.addWidget(container_list)
        
        btn_layout = QHBoxLayout()
        select_ok_button = QPushButton("Select")
        select_cancel_button = QPushButton("Cancel")
        btn_layout.addWidget(select_ok_button)
        btn_layout.addWidget(select_cancel_button)
        select_layout.addLayout(btn_layout)
        
        container_select_dialog.setLayout(select_layout)
        
        # Connect buttons
        select_cancel_button.clicked.connect(container_select_dialog.reject)
        select_ok_button.clicked.connect(lambda: self.showDependenciesForContainer(
            container_list.currentItem().text() if container_list.currentItem() else None,
            container_select_dialog
        ))
        
        container_select_dialog.exec_()
    
    def showDependenciesForContainer(self, container, parent_dialog):
        if not container:
            return    
        parent_dialog.accept()

        dialog = QDialog(self)
        dialog.setWindowTitle("Dependencies")
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout()

        label = QLabel(f"Set dependencies for {container}:")
        layout.addWidget(label)
        dependencyList = QListWidget()
        currentDependencies = self.containerDependencies.get(container, [])

        for cont in self.availableContainers.keys():#ADD ALL ITEMS BUT THE CURRENT CONTAINER
            if cont != container:
                item = QListWidgetItem(cont)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if cont in currentDependencies else Qt.Unchecked)
                dependencyList.addItem(item)
                
        layout.addWidget(dependencyList)
        
        btnLayout = QHBoxLayout()
        okButton = QPushButton("OK")
        cancelButton = QPushButton("Cancel")
        btnLayout.addWidget(okButton)
        btnLayout.addWidget(cancelButton)
        layout.addLayout(btnLayout)
        
        dialog.setLayout(layout)
        
        okButton.clicked.connect(lambda: self.saveDependencies(container, dependencyList, dialog))
        cancelButton.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def saveDependencies(self, container, dependencyList, dialog):
        # Save the selected dependencies
        dependencies = []
        for i in range(dependencyList.count()):
            item = dependencyList.item(i)
            if item.checkState() == Qt.Checked:
                dependencies.append(item.text())
        self.containerDependencies[container] = dependencies
        dialog.accept()

    def updateHostDropdown(self):
        self.hostDropdown.clear()
        # Add only hosts who are not currently at max capacity
        max_containers = self.maxContainersBox.value()
        for host in nm.net.hosts:
            name=host.name
            #print(self.hostContainerCounts.get(name,0),max_containers)
            if self.hostContainerCounts.get(name,0) < max_containers:
                self.hostDropdown.addItem(name)
         
    def autoDeployContainers(self):
        print(self.hostContainerCounts)

        available_hosts = [] #ALL CONTAINERS NOT AT MAX
        max_containers = self.maxContainersBox.value()
        for host in nm.net.hosts:
            name = host.name
            if self.hostContainerCounts.get(name, 0) < max_containers:
                available_hosts.append(name)
            
        available_containers = [] #ALL CONTAINERS NOT RUNNING
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                available_containers.append(container)
                      
        #RANDOM DEPLOYMENT
        for container in available_containers: 
            valid_hosts = [h for h in available_hosts #list comprehension
                          if self.hostContainerCounts.get(h) < self.maxContainersBox.value()]
        
            if not valid_hosts:
                print("All hosts at max capacity")
                continue
            host = random.choice(valid_hosts)
            
            #DEPLOYMENT
            nm.start_container(host, container, self.availableContainers[container])
            container_id = f"{container}_{host}"
            self.runningContainers[container_id] = {"host": host, "container": container}
            self.hostContainerCounts[host] = self.hostContainerCounts.get(host) + 1
            
        self.updateMonitor()
        self.updateHostDropdown()
        self.updateContainerDropdown()
        self.updateLaunchButton()
        self.checkAutoDeploy()

    def checkAutoDeploy(self):
        available_hosts = [] #ALL CONTAINERS NOT AT MAX
        max_containers = self.maxContainersBox.value()
        for host in nm.net.hosts:
            name = host.name
            if self.hostContainerCounts.get(name, 0) < max_containers:
                available_hosts.append(name)
            
        available_containers = [] #ALL CONTAINERS NOT RUNNING
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                available_containers.append(container)
        print("there are available hosts:", bool(available_hosts))
        print("there are available containers: ",bool(available_containers))
        self.autoDeployButton.setEnabled(bool(available_hosts) and bool(available_containers))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()