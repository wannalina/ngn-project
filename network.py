# Enhanced network.py with controller communication

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
import socket
import subprocess
import sys
import os
import time
import json

def kill_previous_instances():
    try:
        subprocess.run(['pkill', '-f', 'topology_generator.py'], stderr=subprocess.DEVNULL)
        subprocess.run(['sudo', 'mn', '-c'], stderr=subprocess.DEVNULL)
        subprocess.run(['sudo', 'pkill', '-f', 'ryu-manager'], stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception as e:
        print(f"Error cleaning up previous instances: {e}")

class NetworkManager:
    def __init__(self):
        self.net = None
        self.sock = None  # Socket to topology generator
        self.controller_sock = None  # Socket to controller
        self.proc = None
        self.controller_process = None
        self.host_mac_mapping = {}  # Store host to MAC mapping

    def start_controller(self):
        print("Starting enhanced Ryu controller in a new xterm window")
        # Use the enhanced controller file
        cmd = [
            "sudo",
            "xterm",
            "-hold",
            "-e",
            "ryu-manager",
            "simple_switch_stp_13.py"  # This should be your enhanced controller
        ]
        self.controller_process = subprocess.Popen(cmd)
        print("Enhanced Ryu controller started in xterm successfully")
        
        # Wait for controller to start and then connect
        time.sleep(3)
        self._connect_to_controller()

    def _connect_to_controller(self):
        """Connect to the controller's socket server"""
        print("Connecting to controller socket")
        try:
            self.controller_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            retries = 10
            for i in range(retries):
                try:
                    self.controller_sock.connect(('localhost', 9998))
                    print("Controller socket connected successfully!")
                    return
                except ConnectionRefusedError:
                    print(f"Controller socket not ready, retrying ({i+1}/{retries})")
                    time.sleep(2)
            raise ConnectionRefusedError("Failed to connect to controller socket")
        except Exception as e:
            print(f"Error connecting to controller: {e}")
            self.controller_sock = None

    def start_network_process(self, num_switches, num_hosts, links_prob):
        kill_previous_instances()
        script_path = os.path.join(os.path.dirname(__file__), "topology_generator.py")
        cmd = [
            'xterm',
            '-e',
            'python3',
            script_path,
            str(num_switches),
            str(num_hosts),
            str(links_prob)
        ]
        print(f"Launching Xterm with command: {' '.join(cmd)}")
        
        try:
            self.proc = subprocess.Popen(cmd)
            print("Xterm launched successfully.")
        except Exception as e:
            print(f"Failed to launch Xterm: {e}")
            raise
    
        print("Waiting for socket server to start")
        time.sleep(5)
        self._connect_to_socket()
        
        # Get host MAC mappings after network is ready
        time.sleep(2)
        self._update_host_mac_mapping()

    def _connect_to_socket(self):
        """Connect to topology generator socket"""
        print("Connecting to topology socket")
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retries = 15
        for i in range(retries):
            try:
                self.sock.connect(('localhost', 9999))
                print("Topology socket connected successfully!")
                return
            except ConnectionRefusedError:
                print(f"Topology socket not ready, retrying ({i+1}/{retries})")
                time.sleep(3)
        raise ConnectionRefusedError("Failed to connect to topology socket after retries")

    def _update_host_mac_mapping(self):
        """Get MAC addresses of all hosts and send to controller"""
        try:
            self.sock.send("GET_HOST_MACS".encode())
            data = self.sock.recv(4096).decode()
            if data.startswith("HOST_MACS"):
                _, json_data = data.split(" ", 1)
                self.host_mac_mapping = json.loads(json_data)
                print(f"Host MAC mapping: {self.host_mac_mapping}")
                
                # Send mapping to controller
                if self.controller_sock:
                    cmd = f"HOST_MAC_MAPPING {json.dumps(self.host_mac_mapping)}"
                    self.controller_sock.send(cmd.encode())
                    response = self.controller_sock.recv(1024).decode()
                    print(f"Controller mapping response: {response}")
        except Exception as e:
            print(f"Error updating host MAC mapping: {e}")

    def update_dependencies(self, dependencies):
        """Send dependency updates to the controller"""
        if not self.controller_sock:
            print("Controller socket not available")
            return
        
        try:
            cmd = f"UPDATE_DEPENDENCIES {json.dumps(dependencies)}"
            self.controller_sock.send(cmd.encode())
            response = self.controller_sock.recv(1024).decode()
            print(f"Dependencies update response: {response}")
        except Exception as e:
            print(f"Error updating dependencies: {e}")

    def start_container(self, host_name, container_name, image_path):
        print(f"Starting container: {host_name}, {container_name}, {image_path}")
        cmd = f"START_CONTAINER {host_name} {container_name} {image_path}"
        self.sock.send(cmd.encode())

        response = self.sock.recv(1024).decode()
        print(f"Container start response: {response}")
        
        # Notify controller about new container
        if self.controller_sock:
            try:
                controller_cmd = f"CONTAINER_STARTED {host_name} {container_name}"
                self.controller_sock.send(controller_cmd.encode())
                controller_response = self.controller_sock.recv(1024).decode()
                print(f"Controller container notification response: {controller_response}")
            except Exception as e:
                print(f"Error notifying controller about container start: {e}")

    def stop_container(self, host_name, container_name):
        cmd = f"STOP_CONTAINER {host_name} {container_name}"
        self.sock.send(cmd.encode())
        
        # Notify controller about container removal
        if self.controller_sock:
            try:
                controller_cmd = f"CONTAINER_STOPPED {host_name} {container_name}"
                self.controller_sock.send(controller_cmd.encode())
                controller_response = self.controller_sock.recv(1024).decode()
                print(f"Controller container removal response: {controller_response}")
            except Exception as e:
                print(f"Error notifying controller about container stop: {e}")

    def stop_all_containers(self):
        cmd = "STOP_ALL"
        self.sock.send(cmd.encode())
        
        # Notify controller about all containers being stopped
        if self.controller_sock:
            try:
                # We could send individual stop notifications, but for simplicity
                # we'll just update with empty dependencies
                controller_cmd = f"UPDATE_DEPENDENCIES {json.dumps({})}"
                self.controller_sock.send(controller_cmd.encode())
                controller_response = self.controller_sock.recv(1024).decode()
                print(f"Controller clear dependencies response: {controller_response}")
            except Exception as e:
                print(f"Error clearing controller dependencies: {e}")

    def shutdown(self):
        try:
            # Stop the Ryu controller
            if self.controller_process:
                print("Stopping Ryu controller")
                self.controller_process.terminate()
                try:
                    self.controller_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.controller_process.kill()
                self.controller_process = None
                subprocess.run(['sudo', 'pkill', '-f', 'ryu-manager'], stderr=subprocess.DEVNULL)
                print("Ryu controller stopped.")

            # Close controller socket
            if self.controller_sock:
                try:
                    self.controller_sock.close()
                except:
                    pass
                self.controller_sock = None

            # Send shutdown to topology generator
            if self.sock:
                try:
                    self.sock.send("SHUTDOWN".encode())
                except:
                    pass
                self.sock.close()
                self.sock = None
                
            # Kill the xterm process
            if self.proc:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                self.proc = None
                
            time.sleep(1)
            print("Network shutdown complete")
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    def get_hosts(self):
        """Get list of hosts from topology generator"""
        self.sock.send("GET_HOSTS".encode())
        data = self.sock.recv(4096).decode()
        return data.split()