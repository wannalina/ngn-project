#!/bin/sh
CONTAINER_NAME=$(basename "$PWD")

CONTROLLER_URL="http://controller:9000/register"

curl -X POST "$CONTROLLER_URL" -H "Content-Type: application/json" \
    -d "{\"container_name\": \"$CONTAINER_NAME\"}"

echo "CONTAINER '$CONTAINER_NAME' REGISTERED."