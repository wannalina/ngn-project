FROM python:3.9-slim

# install postgres
RUN apt-get update && apt-get install -y postgresql

# set postgres env variables
ENV DB_USER=postgres
ENV DB_PASSWORD=newpassword
ENV GENERIC_DB_NAME=postgres
ENV DB_NAME=cities
ENV HOST_IP=localhost
ENV PORT=5432

# check data dir exists
RUN mkdir -p /var/lib/postgresql/data && chown -R postgres:postgres /var/lib/postgresql

# switch to postgres user to initialize db
USER postgres
RUN /usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data

# start postgres and set password
USER root
RUN service postgresql start && sleep 5 && \
    su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'newpassword';\""

# install dependencies
RUN pip install psycopg2-binary

# copy app files
WORKDIR /app
COPY . /app

# start postgres and the db app
CMD service postgresql start && sleep 5 && python3 database_cities.py