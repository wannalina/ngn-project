# Use official Python base image
FROM python:3.9-slim

# Set environment variables to avoid interactive prompts
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y gcc libpq-dev iproute2 iputils-ping net-tools curl && \
    apt-get clean

# Create working directory
WORKDIR /app

# Copy application files
COPY . /app

# Install Python dependencies
RUN pip install psycopg2-binary flask requests threading

# Default environment variables (override at runtime)
ENV DB_NAME=mockdb \
    DB_USER=postgres \
    DB_PASSWORD=secret \
    DB_HOST=127.0.0.1 \
    DB_PORT=5432 \
    GENERIC_DB_NAME=postgres

# Expose Flask default port (for web server)
EXPOSE 5000

# Choose default command for flexibility
# Override via docker run command (e.g., entrypoint python3 server_cities.py)
CMD ["python3", "server_cities.py"]
