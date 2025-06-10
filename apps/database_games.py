from flask import Flask, jsonify

app = Flask(__name__)

FINNISH_GAMES = [
    'Ultrakill',
    'Control',
    'Max Payne',
    'Alan Wake'
]

@app.route('/get-games', methods=['GET'])
def get_finnish_games():
    try:
        return jsonify({'message': FINNISH_GAMES, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error fetching Finnish games: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6002)