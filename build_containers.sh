
# get and loop through all folder names in fake_apps dir on the first hierarchical level
find /fake_apps/ -maxdepth 1 -type d | while read folder_name; do
    echo "Processing: $folder_name"
done