import threading
import time
import psycopg2
from flask import Flask, jsonify
import os
import requests

app = Flask(__name__)

# Close database connection
def connection_close(connection, cursor):
    cursor.close()
    connection.close()

# Connect to database using environment variables
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
def home():
    return "Web server is running"

@app.route('/cities', methods=['GET'])
def get_cities():
    try:
        connection = establish_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM mock_cities_data;")
        rows = cursor.fetchall()
        cities = [{"id": row[0], "city": row[1], "country": row[2]} for row in rows]
        connection_close(connection, cursor)
        return jsonify(cities)
    except Exception as e:
        return f"An error occurred: {e}"

# Poll the /cities endpoint periodically (optional test loop)
def loop_get_cities():
    db_host = os.getenv('APP_SELF_IP', '127.0.0.1')
    while True:
        time.sleep(10)
        try:
            r = requests.get(f"http://{db_host}:5000/cities")
            print(f"Response: {r.json()}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if os.getenv('LOOP_MODE') == '1':
        thread = threading.Thread(target=loop_get_cities, daemon=True)
        thread.start()
    app.run(debug=True, host="0.0.0.0", port=5000)