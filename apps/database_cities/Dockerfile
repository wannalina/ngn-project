
# Dockerfile: For PostgreSQL database container

FROM postgres:13

# Set environment variables for PostgreSQL
ENV POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=secret \
    POSTGRES_DB=mockdb

    pip install psycopg2-binary

# Copy DB init script(s) or application logic into container
COPY . /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# PostgreSQL will automatically run any *.sql or *.sh scripts in the entrypoint directory
# Our application code (database_cities.py) should be run manually or as CMD if desired

# To override default entrypoint and use Python setup script instead:
# CMD ["python3", "database_cities.py"]