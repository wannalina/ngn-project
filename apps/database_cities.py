from flask import Flask, jsonify, request

app = Flask(__name__)

CITIES_LIST = [
    ('Trento', 'Italy'),
    ('Helsinki', 'Finland'),
    ('Bolzano', 'Italy'),
    ('Washington DC', 'USA'),
    ('Barcelona', 'Spain')
]

# route to test if flask app is up and running
@app.route('/', methods=['GET'])
def home():
    return "Test: Database is running!"

# route to get list of cities
@app.route('/get-cities', methods=['GET'])
def get_cities_route():
    try:
        return jsonify({'message': CITIES_LIST, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error fetching cities from database: {e}', 'status_code': 500})

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6000)