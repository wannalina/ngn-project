
FROM python:3.9-slim

# copy app files
WORKDIR /app
COPY . /app

ENV URL_CITIES=http://localhost:5000
ENV URL_ATTRACTIONS=http://localhost:7000

#install flask
RUN pip install flask requests

# expose app port
EXPOSE 8000

# run app
CMD ["python", "server_cityattractions.py"]
