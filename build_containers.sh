#!/bin/bash

# get number of images
folder_count=$(find fake_apps/ -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "NUMBER OF IMAGES TO BUILD: $folder_count"

# get and loop through all folder names in fake_apps dir on the first hierarchical level
find fake_apps/ -mindepth 1 -maxdepth 1 -type d | while read folder_name; do

    # extract folder name from the file path
    image_name=$(basename "$folder_name")

    echo "FOLDER NAME: $image_name"

    echo "BUILDING DOCKER IMAGE."
    docker build -t "$image_name" ./"$image_name"

    echo "SAVING IMAGE TO TAR FILE."
    docker save "$image_name" -o "$image_name.tar"

    echo "LOADING NEW DOCKER IMAGE."
    docker load -i "$image_name.tar"

    echo "RUNNING NEW DOCKER IMAGE."
    docker run --name "$image_name" --net=host "$image_name"
done

docker ps -a
echo "ALL DOCKER IMAGES ARE READY TO EXECUTE."