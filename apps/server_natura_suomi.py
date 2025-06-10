from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/get-finland', methods=['GET'])
def get_finnish_natural_features():
    try:
        db_host = request.args.get('db_host')
        response = requests.get(f'http://10.0.0.{db_host}:6003/get-natura')
        all_features = response.json().get("message")
        
        finnish_features = [feature for feature in all_features if feature[1] == 'Finland']
        
        return jsonify({'message': finnish_features, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error in processing finnish natura: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5003)