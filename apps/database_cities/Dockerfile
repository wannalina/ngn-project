
# Dockerfile: For PostgreSQL database container

FROM postgres:13

# Set environment variables for PostgreSQL
set postgres env variables
ENV DB_NAME=cities
ENV DB_USER=postgres
ENV DB_PASSWORD=newpassword
ENV DB_HOST=localhost
ENV DB_PORT=5432

# Copy DB init script(s) or application logic into container
COPY . /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# PostgreSQL will automatically run any *.sql or *.sh scripts in the entrypoint directory
# Our application code (database_cities.py) should be run manually or as CMD if desired

# To override default entrypoint and use Python setup script instead:
# CMD ["python3", "database_cities.py"]