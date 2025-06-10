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

# run flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
