#!/bin/bash

# get number of images
folder_count=$(find fake_apps/ -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "NUMBER OF IMAGES TO BUILD: $folder_count"

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do

    # check if Dockerfile exists
    if [ -f "$folder_name/Dockerfile" ]; then
        # extract folder name from the file path
        image_name=$(basename "$folder_name")

        echo "Folder name: "$folder_name", Image name: "$image_name""

        echo "BUILDING DOCKER IMAGE."
        docker build -t "$image_name" ./"$folder_name"

        echo "SAVING IMAGE TO TAR FILE."
        docker save "$image_name" -o "$folder_name.tar"

        echo "LOADING NEW DOCKER IMAGE."
        docker load -i "$image_name.tar"
    else
        echo "No Dockerfile found in "$folder_name"."
    fi
    echo "Cleaning up dangling images..."

    echo "Removing dangling images."
    docker image prune -f

done

docker images
echo "ALL DOCKER IMAGES ARE READY TO EXECUTE."

#! TO EXECUTE THIS FILE, USE COMMAND: bash build_images.sh