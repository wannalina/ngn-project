FROM python:3.9-slim

# set working dir
WORKDIR /app

RUN apt-get update && apt-get install -y iproute2 curl

# copy application files into container
COPY . /app

RUN pip install flask requests

ENV DATABASE_URL=http://localhost:6000
ENV CONTROLLER_URL=http://0.0.0.0:6633/register 

# expose app port
EXPOSE 6000

# register the container with controller and start app
CMD bash -c "\
    MAC_ADDRESS=$(ip link show eth0 | awk '/ether/ {print $2}') && \
    IP_ADDRESS=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1) && \
    CONTAINER_NAME=$(hostname) && \
    REGISTRATION_DATA='{ \"mac\": \"$MAC_ADDRESS\", \"ip\": \"$IP_ADDRESS\", \"name\": \"$CONTAINER_NAME\" }' && \
    curl -X POST $CONTROLLER_URL -H 'Content-Type: application/json' -d \"$REGISTRATION_DATA\" && \
    python database_attractions.py"
