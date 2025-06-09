from flask import Flask, jsonify, request
import requests

# init flask app
app = Flask(__name__)

# route to get cities from database
@app.route('/get-cities', methods=['GET'])
def get_cities_route():
    try:
        host = request.args.get('host')

        # get cities list
        response = requests.get(f'http://10.0.0.{host}:6000/get-cities')
        cities_list = response.json().get("message")
        
        return jsonify({'message': cities_list})
    except Exception as e:
        return jsonify({'message': f'Error in processing cities: {e}', 'status_code': 500})

# route to add city to database
@app.route('/add-city', methods=['POST'])
def add_city_route():
    try:
        # get request params
        # request format 'http:localhost:5000/host=4&add-city?city=Stockholm&country=Sweden
        host = request.args.get('host')
        city_param = request.args.get('city')
        country_param = request.args.get('country')

        # add new city
        #new_city = {'city': city_param, 'country': country_param}
        requests.post(f'http://10.0.0.{host}:6000/add-city?city={city_param}&country={country_param}')

        return jsonify({'message': 'City added to database successfully'})
    except Exception as e:
        return jsonify({'message': f"Error adding city to database: {e}"})

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
