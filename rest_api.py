from flask import Flask
from flask.json import jsonify
from tweepy.errors import HTTPException
from twitter_api import user_lookup
from waitress import serve

app = Flask(__name__)

@app.route('/userExist/<name>')
async def user_exist(name):
    try:
        user = await user_lookup(name)
    except HTTPException as e:
        return jsonify({"error": e.api_messages}), e.response.status_code

    return jsonify({ "exist": user != None, "data": dict(user) if user else {} })

def StartAPIServer():
    serve(app, port=8989)