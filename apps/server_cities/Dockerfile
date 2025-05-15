FROM python:3.9-slim

# set postgres env variables
ENV DB_NAME=cities
ENV DB_USER=postgres
ENV DB_PASSWORD=newpassword
ENV DB_HOST=localhost
ENV DB_PORT=5432

# copy app files
WORKDIR /app
COPY . /app

RUN pip install psycopg2-binary flask

CMD python3 server_cities.py && bash ../../libs/register_apps.sh