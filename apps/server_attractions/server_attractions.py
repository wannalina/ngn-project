from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)


@app.route('/add-attraction', methods=['POST'])
def add_attraction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        response = requests.post(f"{os.getenv('DATABASE_URL')}/add-attraction", json=data)
        return response.json(), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/get-attractions', methods=['GET'])
def get_all_attractions():
    try:
        response = requests.get(f"{os.getenv('DATABASE_URL')}/attractions")
        return response.json(), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
