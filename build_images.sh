#!/bin/bash

# get number of images
folder_count=$(find fake_apps/ -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "NUMBER OF IMAGES TO BUILD: $folder_count"

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do

    # extract folder name from the file path
    image_name=$(basename "$folder_name")

    # remove existing Docker image from registry
    docker rmi -f "$image_name"

    # remove existing .tar file if exists in folder
    if [ -f "$folder_name/$image_name.tar" ]; then
        rm $folder_name/$image_name.tar

    # check if Dockerfile exists
    if [ -f "$folder_name/Dockerfile" ]; then
        echo "BUILDING DOCKER IMAGE."
        docker build -t "$image_name" "$folder_name"

        echo "SAVING IMAGE TO TAR FILE."
        docker save "$image_name" -o "$folder_name/$image_name.tar"

        echo "LOADING NEW DOCKER IMAGE."
        docker load -i "$image_name.tar"
    else
        echo "No Dockerfile found in "$folder_name"."
    fi
done

echo "Removing dangling images."
docker image prune -f

docker images
echo "ALL DOCKER IMAGES ARE READY TO EXECUTE."

#! TO EXECUTE THIS FILE, USE COMMAND: bash build_images.sh