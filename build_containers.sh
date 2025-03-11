#!/bin/bash

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do
    echo "Building Docker images."
    docker build -t $folder_name ./$folder_name

    echo "Saving images to .tar files."
    docker save $folder_name -o $folder_name.tar

    echo "Loading new Docker images."
    docker load -i $folder_name.tar

    echo "Running new Docker images."
    docker run --name $folder_name --net=host $folder_name
done

docker ps -a
echo "All Docker images are ready."