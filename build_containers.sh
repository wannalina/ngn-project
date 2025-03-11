#!/bin/bash

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 2 -maxdepth 2 -type f | while read file_name; do
    echo "Building Docker images."
    docker build -t $folder_name .

    echo "Saving images to .tar files."
    docker save $folder_name -o $folder_name

    echo "Loading new Docker images."
    docker load -i $folder_name

    echo "Running new Docker images."
    docker load -i $folder_name
done

docker ps -a
echo "All Docker images are ready."