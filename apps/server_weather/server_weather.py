from flask import Flask
import psycopg2
import signal
import os
import time
import requests

DB_TABLE_VALUES = [('Trento', 'Italy'), ('Helsinki', 'Finland'), ('Bolzano', 'Italy'), ('Washington DC', 'USA'), ('Barcelona', 'Spain')]

# initialize flask app
app = Flask(__name__)

# close db connection
def connection_close(connection, cursor):
    cursor.close()
    connection.close()

# function to handle connection close upon container termination
def handle_sigterm(signum, frame, connection, cursor):
    connection_close(connection, cursor)

# function to connect to db
def establish_connection():
    connection = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    cursor = connection.cursor()
    return connection, cursor

@app.route('/get-weather', methods=['GET'])
def get_weather(city):
    try:
        parameters = {'key': 'YOUR_API_KEY',
                    'place_id': city}

        data = requests.get(os.getenv("API_URL"), parameters).json()
        print('Current temperature in London is {} °C.'.format(data['current']['temperature'])) 
        
        return data
    except Exception as e: 
        print(f"An error occurred in GET: {e}") 

# function to insert weather data to db
def insert_weather(connection, cursor):
    try:
        cities_weather_list = []
        for i in range(len(DB_TABLE_VALUES)-1):
            city = (DB_TABLE_VALUES[i][0]).lower()
            cities_weather_list.append(get_weather(city))

        print("city: ", cities_weather_list)

        # insert values in table
        cursor.executemany("INSERT INTO mock_cities_data (temperature) VALUES (%s) WHERE city=(%s);", cities_weather_list, DB_TABLE_VALUES)
        connection.commit()

    except Exception as e:
        print(f"An error occurred in inserting weather data: {e}")

# function to update existing weather data in db
def update_weather(connection, cursor):
    try:
        cities_weather_list = []
        for i in range(len(DB_TABLE_VALUES)-1):
            city = (DB_TABLE_VALUES[i][0]).lower()
            cities_weather_list.append(get_weather(city))

        print("city: ", cities_weather_list)

        # insert values in table
        cursor.executemany("UPDATE mock_cities_data (temperature) SET temperature=(%s) WHERE city=(%s);", cities_weather_list, DB_TABLE_VALUES)
        connection.commit()
        
        time.sleep(30)
        update_weather(connection, cursor)

    except Exception as e:
        print(f"An error occurred in updating weather data: {e}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6000)

    connection, cursor = establish_connection()

    # register sigterm handler for connection shutdown if container terminated
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_sigterm(signum, frame, connection, cursor))

    insert_weather(connection, cursor)
    update_weather(connection, cursor)

    connection_close(connection, cursor)

