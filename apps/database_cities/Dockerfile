# use official python base image
FROM python:3.9-slim

# set working dir and copy app code
WORKDIR /app
COPY . /app

# install libs
RUN pip install Flask

# expose port
EXPOSE 6000

# run program
CMD ["python3", "database_cities.py"]