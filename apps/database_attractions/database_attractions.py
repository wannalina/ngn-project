from flask import Flask, jsonify
import json

app = Flask(__name__)


# function to load data from file
def load_data():
    with open("data.json", "r", encoding="utf-8") as file:
        return json.load(file)

@app.route('/attractions', methods=['GET'])
def get_attractions():
    data = load_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
