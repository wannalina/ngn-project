FROM python:3.9-slim

WORKDIR /app

RUN pip install psycopg2-binary

COPY database.py /app/database.py

CMD ["python","database.py"]
