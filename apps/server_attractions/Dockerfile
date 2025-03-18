
FROM python:3.9-slim

# copy app files
WORKDIR /app
COPY . /app

ENV DATABASE_URL=http://localhost:6000

#install flask
RUN pip install flask requests

# expose app port
EXPOSE 7000

# run app
CMD ["python", "server_attractions.py"]
