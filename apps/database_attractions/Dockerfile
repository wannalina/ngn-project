FROM python:3.9-slim

# copy app files
WORKDIR /app
COPY . /app


#install flask
RUN pip install flask

# expose app port
EXPOSE 6000

# run app
CMD ["python", "database_attractions.py"]
