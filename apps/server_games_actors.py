from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/get-all', methods=['GET'])
def get_all():
    try:
        act_host = request.args.get('act_host')
        game_host = request.args.get('game_host')

        italian_actors_response = requests.get(f'http://10.0.0.{act_host}:6001/get-actors')
        italian_actors = italian_actors_response.json().get("message")

        finnish_games_response = requests.get(f'http://10.0.0.{game_host}:6002/get-games')
        finnish_games = finnish_games_response.json().get("message")

        combined_data = {
            'italian_actors': italian_actors,
            'finnish_games': finnish_games,
            'description': 'Combined information about Italian actors and Finnish games'
        }
        
        return jsonify({'message': combined_data, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error in processing combined entertainment data: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)