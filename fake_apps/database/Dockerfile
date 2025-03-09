''' 
FROM python:3.9-slim

WORKDIR /app

RUN pip install psycopg2-binary

COPY database.py /app/database.py

CMD ["python","database.py"] 
'''


FROM python:3.9-slim

# install PostgreSQL
RUN apt-get update && apt-get install -y postgresql

# set env variables for postgres
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=newpassword
ENV POSTGRES_DB=cities

# create dir for postgres data
RUN mkdir -p ./postgres/cities
VOLUME ./postgres/cities

# Copy your Python script into the container
WORKDIR /app
COPY . /app

# install dependencies
RUN pip install psycopg2-binary

# start postgres and run script
CMD service postgresql start && sleep 5 && sudo python3 database.py
