import threading
import time
import psycopg2
from flask import Flask, jsonify
import os

import requests

# initialize flask app
app = Flask(__name__)

# close db connection
def connection_close(connection, cursor):
    cursor.close()
    connection.close()

# function to connect to db
def establish_connection():
    connection = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    return connection

@app.route('/', methods=['GET'])
def test():
    while True:
        print("test", flush=True)
    return

# route to fetch data from db table
@app.route('/cities', methods=['GET'])
def get_cities():
    try:
        connection = establish_connection()
        cursor = connection.cursor()
        
        # fetch data from table
        cursor.execute("SELECT * FROM mock_cities_data;")
        rows = cursor.fetchall()
        
        # format data for response
        cities = [{"id": row[0], "city": row[1], "country": row[2]} for row in rows]
        connection_close(connection, cursor)

        print(f"cities: {jsonify(cities)}", flush=True)

        # return response as json
        return jsonify(cities)
    except Exception as e: 
        return f"An error occurred: {e}"

def loop_get_cities():
    while True:
        time.sleep(10)
        try:
            r = requests.get("http://localhost:5000/cities")
            print(f"Response: {r.json()}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # background loop in a separate thread
    thread = threading.Thread(target=loop_get_cities, daemon=True)
    thread.start()
    app.run(debug=True, host="0.0.0.0", port=5000)
