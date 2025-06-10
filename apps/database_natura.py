from flask import Flask, jsonify

app = Flask(__name__)

NATURAL_FEATURES = [
    ('Dolomiti', 'Italy'),
    ('Lago Di Como', 'Italy'),
    ('Lappi', 'Finland'),
    ('Nuuksio kansallispuisto', 'Finland'),
    ('Etna', 'Italy')
]

@app.route('/get-natura', methods=['GET'])
def get_natural_features():
    try:
        return jsonify({'message': NATURAL_FEATURES, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error fetching natura: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6003)