FROM python:3.9

WORKDIR /app

#install flask
RUN pip install flask

COPY . .

# expose app port
EXPOSE 6000

# run app
CMD ["python", "database_attractions.py"]
