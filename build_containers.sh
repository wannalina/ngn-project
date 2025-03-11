#!/bin/bash

# get number of images
folder_count=$(find fake_apps/ -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "Number of images to build: $folder_count"

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do
    echo "BUILDING DOCKER IMAGE."
    docker build -t "$folder_name" ./"$folder_name"

    echo "SAVING IMAGE TO TAR FILE."
    docker save "$folder_name" -o "$folder_name.tar"

    echo "LOADING NEW DOCKER IMAGE."
    docker load -i "$folder_name.tar"

    echo "RUNNING NEW DOCKER IMAGE."
    docker run --name "$folder_name" --net=host "$folder_name"
done

docker ps -a
echo "ALL DOCKER IMAGES ARE READY TO EXECUTE."