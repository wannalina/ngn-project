import socket
import subprocess
import os
import time
import json

def kill_previous_instances():
    try:
        subprocess.run(['pkill', '-f', 'topology/main.py'], stderr=subprocess.DEVNULL) #any running xterm processes
        subprocess.run(['sudo', 'mn', '-c'], stderr=subprocess.DEVNULL) #any running mininet
        #subprocess.run(['pkill', '-f', 'python.*topology_generator'], stderr=subprocess.DEVNULL)
        subprocess.run(['sudo', 'pkill', '-f', 'ryu-manager'], stderr=subprocess.DEVNULL)#any ryu-manager processes
        time.sleep(2)
    except Exception as e:
        print(f"Error cleaning up previous instances: {e}")

class NetworkManager:
    def __init__(self):
        self.net = None
        self.sock = None
        self.proc = None
        self.controller_process= None

    def start_controller(self):
        print("Starting Ryu controller in a new xterm window")
        cmd = [
            "sudo",
            "xterm",
            "-hold",
            "-e",
            "ryu-manager",
            "controller/controller.py"
        ]
        self.controller_process = subprocess.Popen(cmd)
        print("Ryu controller started in xterm successfully")

    def start_network_process(self, num_switches, num_hosts, links_prob):
        kill_previous_instances()
        script_path = os.path.join(os.path.dirname(__file__), "topology/main.py")
        # Use a list for the command arguments instead of shell=True
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
        time.sleep(5)  # Wait 5 seconds before attempting to connect
        self._connect_to_socket()

    def _connect_to_socket(self):
        print("Connecting to socket")
        # Close any existing socket first
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        # Create a new socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retries = 15  # Number of retries
        for i in range(retries):
            try:
                self.sock.connect(('localhost', 9999))
                print("Socket connected successfully!")
                return
            except ConnectionRefusedError:
                print(f"Socket not ready, retrying ({i+1}/{retries})")
                time.sleep(3)  # Wait 3 seconds before retrying
        raise ConnectionRefusedError("Failed to connect to socket after retries")

    def start_container(self, host_name, container_name, image_path):
        print("start container: ",host_name,container_name,image_path)
        cmd = f"START_CONTAINER {host_name} {container_name} {image_path}"
        self.sock.send(cmd.encode())

        response = self.sock.recv(1024).decode() #WAIT FOR ACK RESPONSE
        print(f"Container start response: {response}")

    def stop_container(self, host_name, container_name):
        cmd = f"STOP_CONTAINER {host_name} {container_name}"
        self.sock.send(cmd.encode())

    def stop_all_containers(self):
        cmd = "STOP_ALL"
        self.sock.send(cmd.encode())

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

            if self.sock: # Send a shutdown command to the topology generator
                try:
                    self.sock.send("SHUTDOWN".encode())
                except:
                    pass  # Ignore errors if the socket is already closed
                self.sock.close()
                self.sock = None
                
            # Kill the xterm process
            if self.proc:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)  # Wait up to 5 seconds for normal termination
                except subprocess.TimeoutExpired:
                    self.proc.kill()  # Force kill if it doesn't terminate
                self.proc = None
                
            # Wait a bit to be sure ports are released
            time.sleep(1)
            
            print("Network shutdown complete")
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    def get_hosts(self): #GIVES BACK A FULL LIST OF HOST
        self.sock.send("GET_HOSTS".encode())
        data = self.sock.recv(4096).decode()
        return data.split()  #Host names are space separated
    
    def get_host_info(self, host_name):
        self.sock.send(f"GET_HOST_INFO {host_name}".encode())
        data = self.sock.recv(4096).decode()
        return json.loads(data)

    '''
    # function to fetch mininet host info
    def get_hosts_mn_objects(self, hosts_list):
        try:
            hosts_info = []

            # iterate through hosts in list
            for host in hosts_list:
                # send request to socket server to get host info
                request = f"GET_HOST_INFO {host}"
                self.sock.send(request.encode())
            
                # get and decode json response
                data = self.sock.recv(4096).decode()
                host_info = json.loads(data)

                # validate data
                required_keys = ["host", "host_mac", "dpid"]
                for key in required_keys:
                    if key not in host_info:
                        raise ValueError(f"Missing '{key}' in host info response")
                hosts_info.append(host_info)
            return hosts_info '''

        except Exception as e:
            print(f"Failed to get host info for {host}: {e}")
            return None
