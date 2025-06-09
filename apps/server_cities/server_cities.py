import time
import requests

# function to get cities from 
def get_and_add_cities():
    url = 'http://localhost:6000'
    try:
        # get cities
        cities_res = requests.get(f'{url}/get-cities')
        cities_list = (cities_res.json()).get('message')
        print(f"Cities:\n {cities_list}", flush=True)

        # add city
        query_params = { 'city': 'Stockholm', 'country': 'Sweden'}
        requests.post(f'{url}/add-city', params=query_params)

        # get cities again
        new_cities_res = requests.get(f'{url}/get-cities')
        new_cities_list = (new_cities_res.json()).get('message')
        print(f"Cities:\n {new_cities_list}",flush=True)
    except Exception as e:
        print(f"Error fetching cities from database: {e}")

# run flask app
if __name__ == "__main__":
    while True:
        get_and_add_cities()
        time.sleep(3)