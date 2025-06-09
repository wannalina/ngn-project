#!/bin/bash

# get container name
CONTAINER_NAME=${CONTAINER_NAME:-$(hostname)}

# controller api url
CONTROLLER_URL="http://10.0.2.15:9000/register"

# json request body
JSON_PAYLOAD=$(jq -n --arg name "$CONTAINER_NAME" '{container_name: $name}')

# send registration request to container
curl -X POST -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" \
    "$CONTROLLER_URL"
