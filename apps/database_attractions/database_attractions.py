from flask import Flask, jsonify, request

app = Flask(__name__)

attractions_list = [
    {"city": "Washington, D.C.", "attraction": "Smithsonian Museums", "description": "A collection of world-class museums."},
    {"city": "Bolzano", "attraction": "Runkelstein Castle", "description": "A medieval castle with frescoes and panoramic views."},
    {"city": "Trento", "attraction": "Piazza Duomo", "description": "The heart of Trento, featuring the Neptune Fountain."},
    {"city": "Helsinki", "attraction": "Suomenlinna Fortress", "description": "A UNESCO World Heritage site on an island."},
    {"city": "Barcelona", "attraction": "Park Güell", "description": "A colorful, artistic park designed by Gaudí."}
]

@app.route('/attractions', methods=['GET'])
def get_attractions():
    return jsonify(attractions_list)

@app.route('/add-attraction', methods=['POST'])
def add_attraction():
    try:
        data = request.get_json()
        if not data or 'city' not in data or 'attraction' not in data or 'description' not in data:
            return jsonify({"error": "Invalid data"}), 400
        attractions_list.append(data)
        return jsonify({"message": "Attraction added successfully", "data": data}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
