import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QSpinBox, QGridLayout, QLabel, QPushButton, QVBoxLayout,
    QGroupBox, QComboBox, QScrollArea, QFrame, QHBoxLayout, QDialog, QListWidget,
    QListWidgetItem, QCheckBox,QDoubleSpinBox
)
from PyQt5.QtCore import Qt
from network import NetworkManager
import random
import time

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.nm = NetworkManager()
        self.availableContainers = {}  # name (key) + directory
        self.runningContainers = {}  # container_id (key) + host + container type
        self.hostContainerCounts = {}  # containers per host, hostname(key) + int
        self.containerDependencies = {}  # container dependencies
        self.isRunning=False
        self.dependenciesConfirmed=False
        self.host_list=[]
        self.initUI()

    def initUI(self):
        self.setWindowTitle("CONTAINER DEPLOYMENT")
        #self.setGeometry(100, 100, 550, 650)
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
        self.hostsBox.setRange(1,20)
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
        self.maxContainersBox.setRange(1, 3)
        self.maxContainersBox.setValue(2)
        maxContainersLayout.addWidget(QLabel("Max containers per host: "))
        maxContainersLayout.addWidget(self.maxContainersBox)
        maxContainersLayout.setContentsMargins(5, 0, 5, 0)

        # Add layouts to grid
        topoLayout.addLayout(switchesLayout, 0, 0)
        topoLayout.addLayout(hostsLayout, 0, 1)
        topoLayout.addLayout(linkProbLayout, 0, 2)
        topoLayout.addLayout(maxContainersLayout, 1, 0, 1, 3)

        # RUN and STOP buttons
        self.run = QPushButton("RUN")
        self.stop = QPushButton("STOP")
        topoLayout.addWidget(self.run, 2, 0, 1, 1, Qt.AlignRight)
        topoLayout.addWidget(self.stop, 2, 2, 1, 1, Qt.AlignLeft)
        topoGroupBox.setLayout(topoLayout)
        mainLayout.addWidget(topoGroupBox)
        ##TOPOLOGY FINISHED

        #DEPENDENCY AREA
        self.dependencyGroupBox = QGroupBox("DEPENDENCIES")
        depenencyLayout=QHBoxLayout()

        # Dependency Button
        self.dependencyButton = QPushButton("Select Dependencies")
        self.dependencyButton.clicked.connect(self.openDependencyDialog)
        depenencyLayout.addWidget(self.dependencyButton)
        #Confirm dependencies
        self.confirmDependencyButton = QPushButton("Confirm Dependencies")
        self.confirmDependencyButton.clicked.connect(self.confirmDependency)
        depenencyLayout.addWidget(self.confirmDependencyButton)

        self.dependencyGroupBox.setLayout(depenencyLayout)
        mainLayout.addWidget(self.dependencyGroupBox)
        #FINISHED DEPENDENCY AREA

        #DOCKER AREA
        self.containerGroupBox = QGroupBox("DOCKERS")
        containerLayout = QGridLayout()

        # Host and Container dropdowns
        dockerHostsLayout = QHBoxLayout()
        dockerHostsLayout.addWidget(QLabel("Hosts: "))
        self.hostDropdown = QComboBox()
        self.hostDropdown.currentTextChanged.connect(self.updateLaunchButton)
        dockerHostsLayout.addWidget(self.hostDropdown)

        dockerContainersLayout = QHBoxLayout()
        dockerContainersLayout.addWidget(QLabel("Containers: "))
        self.containerDropdown = QComboBox()
        self.containerDropdown.currentTextChanged.connect(self.updateLaunchButton)
        dockerContainersLayout.addWidget(self.containerDropdown)

        self.launchButton = QPushButton("Start container")
        containerLayout.addLayout(dockerHostsLayout, 0, 0)
        containerLayout.addLayout(dockerContainersLayout, 0, 1)
        containerLayout.addWidget(self.launchButton, 0, 2)

        # Auto Deploy Button
        self.autoDeployButton = QPushButton("Auto Deploy All Containers")
        containerLayout.addWidget(self.autoDeployButton, 1, 0, 1, 3, Qt.AlignHCenter)

        # Active Containers List
        activeContainersBox = QGroupBox("Active Containers")
        self.activeContainerLayout = QVBoxLayout()
        activeContainersBox.setLayout(self.activeContainerLayout)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(activeContainersBox)
        containerLayout.addWidget(scrollArea, 2, 0, 1, 3)

        # Stop All Button
        self.stopAllButton = QPushButton("Shut down ALL containers")
        containerLayout.addWidget(self.stopAllButton, 3, 0, 1, 3, Qt.AlignHCenter)

        self.containerGroupBox.setLayout(containerLayout)
        mainLayout.addWidget(self.containerGroupBox)

        self.updateEnables()
        
        self.run.setFixedSize(100, 35)
        self.stop.setFixedSize(100, 35)
        self.launchButton.setFixedSize(130, 30)
        self.dependencyButton.setFixedSize(200, 35)
        self.autoDeployButton.setFixedSize(200, 45)
        self.stopAllButton.setFixedSize(200, 45)
        self.confirmDependencyButton.setFixedSize(200, 35)
        
        # Connect signals
        self.run.clicked.connect(self.run_clicked)
        self.stop.clicked.connect(self.stop_clicked)
        self.launchButton.clicked.connect(self.startContainer)
        self.stopAllButton.clicked.connect(self.stopAllContainers)
        self.autoDeployButton.clicked.connect(self.autoDeployContainers)
        self.setLayout(mainLayout)

    def run_clicked(self):
        print("RUN button clicked")
        self.isRunning=True
        params = (
            self.switchesBox.value(),
            self.hostsBox.value(),
            self.linkProbBox.value()
        )
        print(f"Starting network with params: {params}")
        self.nm.start_network_process(*params)
        self.host_list = self.nm.get_hosts()
        self.nm.start_controller()
        

    #ON THE FLY ADDS 
        self.updateEnables()
        self.findContainers()
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.checkAutoDeploy()
    #############
    def stop_clicked(self):
            print("STOP button clicked")
            self.isRunning=False
            self.dependenciesConfirmed=False
            self.stopAllContainers()
            self.nm.shutdown()
            self.updateEnables()

    def closeEvent(self, event):
        if self.isRunning:
            print("Window closing: Stopping network first")
            self.stopAllContainers()
            self.nm.shutdown()
            self.isRunning = False
        event.accept()

    def updateEnables(self):
        self.containerGroupBox.setEnabled(self.isRunning and self.dependenciesConfirmed)  
        self.run.setEnabled(not self.isRunning)
        self.stop.setEnabled(self.isRunning)
        self.linkProbBox.setEnabled(not self.isRunning)
        self.hostsBox.setEnabled(not self.isRunning)
        self.switchesBox.setEnabled(not self.isRunning)
        self.maxContainersBox.setEnabled(not self.isRunning)
        self.dependencyGroupBox.setEnabled(self.isRunning and not self.dependenciesConfirmed)

    def updateLaunchButton(self):
        if self.containerGroupBox.isEnabled():
            container = self.containerDropdown.currentText()
            host = self.hostDropdown.currentText()
            max_containers = self.maxContainersBox.value()

            # Check if the host has reached its container limit
            at_limit = False
            if host:
                current_count = self.hostContainerCounts.get(host,0) #method sometimes is called before current is initliazied as 0
                at_limit = current_count >= max_containers

        # Enable the launch button only if:
        # 1. A container is selected
        # 2. The host is not at its container limit
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
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                self.containerDropdown.addItem(container)

    def startContainer(self):
        host = self.hostDropdown.currentText()
        container = self.containerDropdown.currentText()
        if not container: 
            return
        self.nm.start_container(host, container, self.availableContainers[container])
        container_id = f"{container}_{host}"
        self.runningContainers[container_id] = {"host": host, "container": container}
        self.hostContainerCounts[host] = self.hostContainerCounts.get(host,0) + 1
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.updateMonitor()
        self.checkAutoDeploy()

    def stopAllContainers(self):
        self.nm.stop_all_containers()
        self.runningContainers = {}
        self.hostContainerCounts = {host: 0 for host in self.hostContainerCounts}
        self.updateMonitor()
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.checkAutoDeploy()

    def updateMonitor(self):
        self.cleanMonitor()
        for container_id, data in self.runningContainers.items():
            container_frame = QFrame()
            container_frame.setFrameShape(QFrame.StyledPanel)
            container_layout = QHBoxLayout()
            container_frame.setFixedSize(478, 60)
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
        self.nm.stop_container(host, container)
        container_id = f"{container}_{host}"
        if container_id in self.runningContainers:
            del self.runningContainers[container_id]
            self.hostContainerCounts[host] = self.hostContainerCounts.get(host) - 1
            self.updateContainerDropdown()
            self.updateHostDropdown()
            self.updateMonitor()
            self.checkAutoDeploy()

    def openDependencyDialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Container Dependencies")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout()

        label = QLabel("Select a container to set dependencies:")
        layout.addWidget(label)

        container_list = QListWidget()
       #FETCH ALL CONTAINERS
        all_containers = set(self.availableContainers.keys())
        for container in all_containers:
            container_list.addItem(container)
        layout.addWidget(container_list)

        btn_layout = QHBoxLayout()
        select_ok_button = QPushButton("Select")
        select_cancel_button = QPushButton("Cancel")
        btn_layout.addWidget(select_ok_button)
        btn_layout.addWidget(select_cancel_button)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        # Connect buttons
        select_cancel_button.clicked.connect(dialog.reject)
        select_ok_button.clicked.connect(lambda: self.showDependenciesForContainer(container_list.currentItem().text(), dialog))
        dialog.exec_()

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
        currentDependencies = self.containerDependencies.get(container, {})
        for cont in self.availableContainers.keys():
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
        dependencies = set()
        for i in range(dependencyList.count()):
            item = dependencyList.item(i)
            if item.checkState() == Qt.Checked:
                dependencies.add(item.text())
        self.containerDependencies[container] = dependencies
        dialog.accept()

    def updateHostDropdown(self):
            self.hostDropdown.clear()
            try:
                max_containers = self.maxContainersBox.value()
                for host in self.host_list:
                    if self.hostContainerCounts.get(host, 0) < max_containers:
                        self.hostDropdown.addItem(host)
            except Exception as e:
                print(f"Error updating host dropdown: {e}")

         
    def autoDeployContainers(self):
        print(self.hostContainerCounts)
        available_hosts = [] #ALL CONTAINERS NOT AT MAX
        max_containers = self.maxContainersBox.value()
        for host in self.host_list:
            if self.hostContainerCounts.get(host, 0) < max_containers:
                available_hosts.append(host)
        available_containers = [] #ALL CONTAINERS NOT RUNNING
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                available_containers.append(container)
        
        #available_hosts = [host.name for host in self.host_list if self.hostContainerCounts.get(host.name, 0) < self.maxContainersBox.value()]
        #available_containers = [container for container in self.availableContainers.keys() if not any(entry["container"] == container for entry in self.runningContainers.values())]
        #RANDOM DEPLOYMENT
        for container in available_containers: 
            valid_hosts = [h for h in available_hosts #list comprehension
                          if self.hostContainerCounts.get(h,0) < max_containers]
        
            if not valid_hosts:
                print("All hosts at max capacity")
                continue
            host = random.choice(valid_hosts)
            #DEPLOYMENT
            self.nm.start_container(host, container, self.availableContainers[container])
            container_id = f"{container}_{host}"
            self.runningContainers[container_id] = {"host": host, "container": container}
            self.hostContainerCounts[host] = self.hostContainerCounts.get(host, 0) + 1
            

        self.updateMonitor()
        self.updateHostDropdown()
        self.updateContainerDropdown()
        self.checkAutoDeploy()
    
    def checkAutoDeploy(self):
        available_hosts = [] #ALL CONTAINERS NOT AT MAX
        max_containers = self.maxContainersBox.value()
        for host in self.host_list:
            if self.hostContainerCounts.get(host, 0) < max_containers:
                available_hosts.append(host)
        available_containers = [] #ALL CONTAINERS NOT RUNNING
        for container in self.availableContainers.keys():
            if not any(entry["container"] == container for entry in self.runningContainers.values()):
                available_containers.append(container)
        
        print("there are available hosts:", bool(available_hosts))
        print("there are available containers: ",bool(available_containers))
        self.autoDeployButton.setEnabled(bool(available_hosts) and bool(available_containers))

        self.stopAllButton.setEnabled(bool(self.runningContainers))

    def confirmDependency(self):
        self.dependenciesConfirmed = True
        print("raw dependencies", self.containerDependencies)
       
        updated_dependencies = {} #FILL UP COPY OTHERWISE "DICTIONARY CHANGED SIZE WHILE ITERATING"
        updated_dependencies = self.containerDependencies.copy()
    
        for container, deps in self.containerDependencies.items():
            for dependency in deps:
                #if dependency not in updated_dependencies:
                updated_dependencies[dependency] = set()
                updated_dependencies[dependency].add(container)
    
        self.containerDependencies = updated_dependencies
        print("updated dependencies", self.containerDependencies)
        self.updateEnables()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
