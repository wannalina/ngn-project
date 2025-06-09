from flask import Flask, jsonify
import requests

# init flask app
app = Flask(__name__)

# route to get cities from database
@app.route('/get-cities', methods=['GET'])
def get_cities_route():
    try:
        #db_host = requests.args.get('host')

        # get cities list
        response = requests.get(f'http://0.0.0.0/get-cities')
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
        #db_host = requests.args.get('host')
        city_param = requests.args.get('city')
        country_param = requests.args.get('country')

        # add new city
        new_city = {'city': city_param, 'country': country_param}
        requests.post(f'http://0.0.0.0/add-city', params=new_city)

        return jsonify({'message': 'City added to database successfully'})
    except Exception as e:
        return jsonify({'message': f"Error adding city to database: {e}"})

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
