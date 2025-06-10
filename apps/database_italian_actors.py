from flask import Flask, jsonify

app = Flask(__name__)

ITALIAN_ACTORS = [
    ('Sophia Loren'),
    ('Pierfrancesco Favino'),
    ('Monica Bellucci'),
    ('Alessandro Borghi'),
    ('Luca Marinelli')
]

@app.route('/get-italian-actors', methods=['GET'])
def get_italian_actors():
    try:
        return jsonify({'message': ITALIAN_ACTORS, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error fetching Italian actors: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6001)