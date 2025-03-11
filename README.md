# ngn-project
Next Generation Networks course project on the automatic deployment of containers


COMMANDS THAT YOU MIGHT NEED:

1. Run application: `sudo python3 gui.py`

2. Docker
    2.1. Build all images: `bash build_images.sh`
    2.2. Build single image: `docker build -t image_name .`
    2.3. Save .tar file of the image: `docker save image_name -o image_name.tar`
    2.4. Load Docker image: `docker load -i image_name.tar`
    2.5. Run Docker container: `docker run -d --name image_name --net=host image_name`
    2.6. Check status of existing containers: `docker ps -a`
    2.7. Check logs of a running Docker container: `docker logs -f container_name`
    2.8. Stop a running container: `docker stop container_name`
    2.9. Remove a container: `docker rm container_name`
    2.10. List all created images in registry: `docker images`
    2.11. Remove a Docker image from registry: `docker rmi image_name`

3. See the output of the server_cities.py: `curl http://localhsot:5000/cities`