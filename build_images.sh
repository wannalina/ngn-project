#!/bin/bash

# get number of images
folder_count=$(find fake_apps/ -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "NUMBER OF IMAGES TO BUILD: $folder_count"

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do

    # extract folder name from the file path
    image_name=$(basename "$folder_name")

    # check if Docker image exists in registry
    if docker images -q "$image_name" >/dev/null 2>&1; then
        echo "REMOVING EXISTING DOCKER IMAGE: $image_name"
        docker rmi -f "$image_name"
    fi

    # check if .tar file exists
    if [ -f "$folder_name/$image_name.tar" ]; then
        echo "REMOVING EXISTING DOCKER IMAGE FILE."
        rm $folder_name/$image_name.tar
    fi
done

echo "Removing dangling images."
docker image prune -f

docker images
echo "ALL DOCKER IMAGES ARE READY TO EXECUTE."

#! TO EXECUTE THIS FILE, USE COMMAND: bash build_images.sh