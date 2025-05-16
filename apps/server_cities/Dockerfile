# specify docker version
FROM python:3.9-slim

# set env variables
ENV DB_NAME=cities
ENV DB_USER=postgres
ENV DB_PASSWORD=newpassword
ENV DB_HOST=localhost
ENV DB_PORT=5432

# set working dir inside container
WORKDIR /app

# copy required directories
COPY apps/server_cities /app
COPY libs/register_apps.sh /app/libs/register_apps.sh

# verify regitser_apps.sh is executable
RUN chmod +x /app/libs/register_apps.sh

# install dependencies
RUN pip install psycopg2-binary flask

# run register_apps.sh and start server
CMD bash -c "/app/libs/register_apps.sh && python3 server_cities.py"
