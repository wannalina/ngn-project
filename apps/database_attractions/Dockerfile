FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy application files into the container
COPY . /app

# Install required Python packages
RUN pip install flask requests

# Install bash and iproute2 for network utilities
RUN apt-get update && apt-get install -y iproute2 bash netcat

# Expose the app port (example port from controller)
EXPOSE 6000

# Get MAC and IP address and register with the SDN Controller
CMD bash -c "\
  MAC_ADDRESS=$(ip link show eth0 | awk '/ether/ {print $2}') && \
  IP_ADDRESS=$(ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1) && \
  CONTAINER_NAME=$(hostname) && \
  REGISTRATION_DATA='{\"mac\": \"$MAC_ADDRESS\", \"ip\": \"$IP_ADDRESS\", \"name\": \"$CONTAINER_NAME\"}' && \
  echo -n $REGISTRATION_DATA | nc 127.0.0.1 6000 && \
  python3 database_attractions.py"  # Replace with your actual application start command
