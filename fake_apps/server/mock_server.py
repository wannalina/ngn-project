import psycopg2
from flask import Flask, jsonify

# database params
DB_NAME = "cities"
DB_USER = "postgres"
DB_PASSWORD = "newpassword"
DB_HOST = "localhost"
DB_PORT = "5432"

# initialize flask app
app = Flask(__name__)

# close db connection
def connection_close(connection, cursor):
    cursor.close()
    connection.close()

# function to connect to db
def establish_connection():
    connection = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    return connection

# route to fetch data from db table
@app.route('/', methods=['GET'])
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
        return "An error occurred"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
