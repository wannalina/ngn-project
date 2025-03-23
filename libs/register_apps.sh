#!/bin/sh

# get container ID
CONTAINER_NAME=$(basename"$PWD")

# SDN controller API address
CONTROLLER_URL="http:0.0.0.0:6633/register"

# register container to controller
# curl -X POST "$CONTROLLER_URL" -H "Content-Type: application/json" \
#     -d '{"container_name": "'"$CONTAINER_NAME"'", "hostname": "'"$(hostname)"'"}'

echo "CONTAINER '$CONTAINER_NAME' REGISTERED."
