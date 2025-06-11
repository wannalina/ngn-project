# Next Generation Networks Project
SDN network allowing traffic only between selected hosts and services


## 1. Install dependencies

Open a terminal in the project directory and run:

    pip install -r requirements.txt

## 2. Run the GUI

    sudo python3 gui.py

## 3. Applications

Before runninng the apps, you should set the adequate dependencies.
When you have run the desired apps, you can open the terminal's xterm window by the mininet console.
There you can use the curl command to query the application.

### example 
`curl http://10.0.0.1:5000/get-cities?host=2`

if we're trying to connect to the application running on host 1 to query the application running on host 2

See `commands.txt` for the complete list of endpoints
