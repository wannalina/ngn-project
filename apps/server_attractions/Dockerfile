FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install required system packages (iproute2 and curl)
RUN apt-get update && apt-get install -y iproute2 curl

# Copy application files into the container
COPY . /app

# Install Python dependencies
RUN pip install flask requests

# Set the environment variable for the database URL
ENV DATABASE_URL=http://localhost:7000
ENV CONTROLLER_URL=http://controller-ip:6000/register  # Update this with the actual controller URL

# Expose the app port (as the application runs on port 7000)
EXPOSE 7000

# Register the container with the SDN Controller and start the application
CMD bash -c "\
    MAC_ADDRESS=$(ip link show eth0 | awk '/ether/ {print $2}') && \
    IP_ADDRESS=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1) && \
    CONTAINER_NAME=$(hostname) && \
    REGISTRATION_DATA='{ \"mac\": \"$MAC_ADDRESS\", \"ip\": \"$IP_ADDRESS\", \"name\": \"$CONTAINER_NAME\" }' && \
    curl -X POST $CONTROLLER_URL -H 'Content-Type: application/json' -d \"$REGISTRATION_DATA\" && \
    python server_attractions.py"
