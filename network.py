from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
import socket
import subprocess
import sys
import os
import time

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
        self.sock = None
        self.proc = None
        self.controller_process = None

    def start_controller(self):
        print("Starting Ryu controller in a new xterm window")
        cmd = [
            "sudo",
            "xterm",
            "-hold",
            "-e",
            "ryu-manager",
            "simple_switch_stp_13.py"
        ]
        self.controller_process = subprocess.Popen(cmd)
        print("Ryu controller started in xterm successfully")

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

    def _connect_to_socket(self):
        print("Connecting to socket")
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
                print("Socket connected successfully!")
                return
            except ConnectionRefusedError:
                print(f"Socket not ready, retrying ({i+1}/{retries})")
                time.sleep(3)
        raise ConnectionRefusedError("Failed to connect to socket after retries")

    def start_container(self, host_name, container_name, image_path):
        print(f"start container: {host_name}, {container_name}, {image_path}")
        cmd = f"START_CONTAINER {host_name} {container_name} {image_path}"
        self.sock.send(cmd.encode())

        response = self.sock.recv(1024).decode()
        print(f"Container start response: {response}")
        
        # Verify container is actually running
        time.sleep(1)  # Give container time to start
        self.verify_container_status(host_name, container_name)

    def verify_container_status(self, host_name, container_name):
        """Verify that a container is actually running on the specified host"""
        try:
            # Get list of running containers
            cmd = "LIST_CONTAINERS"
            self.sock.send(cmd.encode())
            response = self.sock.recv(1024).decode()
            
            expected_entry = f"{host_name}:{container_name}"
            if expected_entry in response:
                print(f"✓ Container {container_name} verified running on {host_name}")
            else:
                print(f"✗ Container {container_name} NOT found running on {host_name}")
                print(f"Current running containers: {response}")
                
        except Exception as e:
            print(f"Error verifying container status: {e}")

    def stop_container(self, host_name, container_name):
        cmd = f"STOP_CONTAINER {host_name} {container_name}"
        self.sock.send(cmd.encode())
        print(f"Stopped container {container_name} on {host_name}")

    def stop_all_containers(self):
        cmd = "STOP_ALL"
        self.sock.send(cmd.encode())
        print("Stopped all containers")

    def get_running_containers(self):
        """Get list of currently running containers"""
        try:
            cmd = "LIST_CONTAINERS"
            self.sock.send(cmd.encode())
            response = self.sock.recv(1024).decode()
            
            if response == "NO_CONTAINERS":
                return []
            
            containers = []
            for entry in response.split():
                if ':' in entry:
                    host, container = entry.split(':', 1)
                    containers.append({'host': host, 'container': container})
            
            return containers
        except Exception as e:
            print(f"Error getting running containers: {e}")
            return []

    def debug_network_status(self):
        """Debug method to check network and container status"""
        print("\n=== NETWORK DEBUG INFO ===")
        try:
            containers = self.get_running_containers()
            print(f"Running containers: {containers}")
            
            hosts = self.get_hosts()
            print(f"Available hosts: {hosts}")
            
        except Exception as e:
            print(f"Error during debug: {e}")

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

            if self.sock:
                try:
                    self.sock.send("SHUTDOWN".encode())
                except:
                    pass
                self.sock.close()
                self.sock = None
                
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
        self.sock.send("GET_HOSTS".encode())
        data = self.sock.recv(4096).decode()
        return data.split()