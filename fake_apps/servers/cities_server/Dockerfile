FROM python:3.9-slim

# database params
ENV DB_NAME = "cities"
ENV DB_USER = "postgres"
ENV DB_PASSWORD = "newpassword"
ENV DB_HOST = "localhost"
ENV DB_PORT = "5432"

WORKDIR /app

RUN pip install psycopg2-binary flask

COPY mock_server.py /app/mock_server.py

CMD ["python3","cities_server.py"]
