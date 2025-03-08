FROM python:3.9-slim

WORKDIR /app

RUN pip install psycopg2-binary flask

COPY mock_server.py /app/mock_server.py

CMD ["python","mock_server.py"]
