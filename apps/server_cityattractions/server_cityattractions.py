import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def get_cities_and_attractions():
    try:
        response = []

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        response_cities = requests.get(f"{os.getenv('URL_CITIES')}/cities")
        response_attractions = requests.get(f"{os.getenv('URL_ATTRACTIONS')}/get-attractions")

        if response_cities.status_code != 200 or response_attractions.status_code != 200:
            return jsonify({"error": "Failed to retrieve data from services"}), 500

        cities = response_cities.json()
        attractions = response_attractions.json()

        for city in cities:
            city_name = city.get("city")
            city_attractions = [a for a in attractions if a["city"] == city_name]
            
            response.append({
                "city": city_name,
                "country": city.get("country", "Unknown"),
                "attractions": city_attractions
            })

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
