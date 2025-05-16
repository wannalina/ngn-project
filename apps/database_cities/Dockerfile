FROM python:3.9-slim

# install postgresql dependency
RUN apt-get update && apt-get install -y postgresql

# set env variables
ENV DB_USER=postgres
ENV DB_PASSWORD=newpassword
ENV GENERIC_DB_NAME=postgres
ENV DB_NAME=cities
ENV HOST_IP=localhost
ENV PORT=5432

# set up working dir
RUN mkdir -p /var/lib/postgresql/data && chown -R postgres:postgres /var/lib/postgresql

# initialize database and set password
USER postgres
RUN /usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data
USER root
RUN service postgresql start && sleep 5 && \
    su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'newpassword';\""

# install deendencies
RUN pip install psycopg2-binary

# copy app files and register_apps.sh
WORKDIR /app
COPY apps/database_cities /app
COPY libs/register_apps.sh /app/libs/register_apps.sh

# verify register_apps.sh is executable
RUN chmod +x /app/libs/register_apps.sh

# start database, run application and regitser to controller
CMD bash -c "service postgresql start && sleep 5 && python3 database_cities.py && /app/libs/register_apps.sh"
