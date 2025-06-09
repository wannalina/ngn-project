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

# route to add a new city to the list
@app.route('/add-city', methods=['POST'])
def add_city_route():
    try:
        # get query params
        city_param = request.args.get('city')
        country_param = request.args.get('country')

        # add new city to list
        new_entry = (city_param, country_param)
        CITIES_LIST.append(new_entry)

        return jsonify({'message': 'New city added successfully', 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error adding new city to list: {e}', 'status_code': 500})

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6000)