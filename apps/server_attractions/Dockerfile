
FROM python:3.9-slim

# copy app files
WORKDIR /app
COPY . /app

ENV DATABASE_URL = http://fake_database:6000

#install flask
RUN pip install flask

# expose app port
EXPOSE 7000

# run app
CMD ["python", "database_attractions.py"]
