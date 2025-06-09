from flask import Flask
import requests

# initialize flask app
app = Flask(__name__)

# function to get cities from 
def get_and_add_cities():
    url = 'http://localhost:5000'
    try:
        # get cities
        cities_list = requests.get(f'{url}/get-cities').message
        print(f"Cities:\n {cities_list}")

        # add city
        query_params = { 'city': 'Stockholm', 'country': 'Sweden'}
        requests.post(f'{url}/add-city', params=query_params)

        # get cities again
        new_cities_list = requests.get(f'{url}/get-cities').message
        print(f"Cities:\n {cities_list}")
    except Exception as e:
        print(f"Error fetching cities from database: {e}")

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    get_and_add_cities()