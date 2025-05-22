# Modifications needed for gui.py to integrate with dependency-aware controller

# Add this method to the MainWindow class in gui.py:

def confirmDependency(self):
    """Enhanced dependency confirmation that updates the controller"""
    self.dependenciesConfirmed = True
    print("Raw dependencies:", self.containerDependencies)
   
    # Create bidirectional dependencies as before
    updated_dependencies = self.containerDependencies.copy()

    for container, deps in self.containerDependencies.items():
        for dependency in deps:
            if dependency not in updated_dependencies:
                updated_dependencies[dependency] = set()
            updated_dependencies[dependency].add(container)

    # Convert sets to lists for JSON serialization
    json_dependencies = {}
    for container, deps in updated_dependencies.items():
        json_dependencies[container] = list(deps) if isinstance(deps, set) else deps

    self.containerDependencies = updated_dependencies
    print("Updated dependencies:", self.containerDependencies)
    
    # Send dependencies to the controller via NetworkManager
    try:
        self.nm.update_dependencies(json_dependencies)
        print("Dependencies sent to controller successfully")
    except Exception as e:
        print(f"Error sending dependencies to controller: {e}")
    
    self.updateEnables()

# Also modify the startContainer method to notify about dependency changes:

def startContainer(self):
    """Enhanced container start with dependency notification"""
    host = self.hostDropdown.currentText()
    container = self.containerDropdown.currentText()
    if not container: 
        return
        
    self.nm.start_container(host, container, self.availableContainers[container])
    container_id = f"{container}_{host}"
    self.runningContainers[container_id] = {"host": host, "container": container}
    self.hostContainerCounts[host] = self.hostContainerCounts.get(host, 0) + 1
    
    self.updateContainerDropdown()
    self.updateHostDropdown()
    self.updateMonitor()
    self.checkAutoDeploy()
    
    # Update controller with current dependencies after container start
    if self.dependenciesConfirmed and self.containerDependencies:
        try:
            json_dependencies = {}
            for cont, deps in self.containerDependencies.items():
                json_dependencies[cont] = list(deps) if isinstance(deps, set) else deps
            self.nm.update_dependencies(json_dependencies)
            print("Dependencies refreshed in controller after container start")
        except Exception as e:
            print(f"Error refreshing dependencies in controller: {e}")

# Modify stop_container method as well:

def stop_container(self, host, container):
    """Enhanced container stop with dependency notification"""
    self.nm.stop_container(host, container)
    container_id = f"{container}_{host}"
    if container_id in self.runningContainers:
        del self.runningContainers[container_id]
        self.hostContainerCounts[host] = self.hostContainerCounts.get(host) - 1
        self.updateContainerDropdown()
        self.updateHostDropdown()
        self.updateMonitor()
        self.checkAutoDeploy()
        
        # Update controller with current dependencies after container stop
        if self.dependenciesConfirmed and self.containerDependencies:
            try:
                json_dependencies = {}
                for cont, deps in self.containerDependencies.items():
                    json_dependencies[cont] = list(deps) if isinstance(deps, set) else deps
                self.nm.update_dependencies(json_dependencies)
                print("Dependencies refreshed in controller after container stop")
            except Exception as e:
                print(f"Error refreshing dependencies in controller: {e}")

# Add a new method for real-time dependency updates:

def updateDependenciesInController(self):
    """Send current dependency state to controller"""
    if not self.dependenciesConfirmed or not hasattr(self, 'nm') or not self.nm:
        return
        
    try:
        json_dependencies = {}
        for container, deps in self.containerDependencies.items():
            json_dependencies[container] = list(deps) if isinstance(deps, set) else deps
        
        self.nm.update_dependencies(json_dependencies)
        print("Dependencies synchronized with controller")
    except Exception as e:
        print(f"Error synchronizing dependencies with controller: {e}")

# Modify the saveDependencies method to provide real-time updates:

def saveDependencies(self, container, dependencyList, dialog):
    """Enhanced save dependencies with real-time controller updates"""
    dependencies = set()
    for i in range(dependencyList.count()):
        item = dependencyList.item(i)
        if item.checkState() == Qt.Checked:
            dependencies.add(item.text())
    
    self.containerDependencies[container] = dependencies
    dialog.accept()
    
    # If dependencies are already confirmed, update controller immediately
    if self.dependenciesConfirmed:
        self.updateDependenciesInController()

# Add this method for debugging dependency state:

def debugDependencyState(self):
    """Debug method to print current dependency and container state"""
    print("=== DEPENDENCY DEBUG STATE ===")
    print(f"Dependencies confirmed: {self.dependenciesConfirmed}")
    print(f"Container dependencies: {self.containerDependencies}")
    print(f"Running containers: {self.runningContainers}")
    print(f"Host container counts: {self.hostContainerCounts}")
    print("==============================")

# Also add a status indicator to show controller connection:

def updateControllerStatus(self):
    """Update GUI to show controller connection status"""
    # You could add a status label to the GUI to show if controller is connected
    # This would require adding a QLabel to the UI in initUI()
    pass