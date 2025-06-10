from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/get-italy', methods=['GET'])
def get_italian_natural_features():
    try:
        db_host = request.args.get('db_host')
        response = requests.get(f'http://10.0.0.{db_host}:6003/get-natura')
        all_features = response.json().get("message")
        
        italian_features = [feature for feature in all_features if feature[1] == 'Italy']
        
        return jsonify({'message': italian_features, 'status_code': 200})
    except Exception as e:
        return jsonify({'message': f'Error in processing italian nature: {e}', 'status_code': 500})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)