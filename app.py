from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from scipy.spatial.distance import euclidean
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from emotion_analysis import preProcessEmotionModel

import uuid
import jwt
import datetime
import requests
import numpy as np

# RUN REQUIREMENT.TXT FILE TO INSTALL DEPENDENCIES
# cd to the directory where requirements.txt is located.
# activate your virtualenv.
# run: pip install -r requirements.txt in your shell.


# we import requests to make HTTP requests to the Brain Shop API
# library installs and important pre-requisites
# $ pip install requests
# datetime to create an expiration for jwt
# jwt for generating json web token -
# we are using PyJWT not JWT... so $ pip uninstall JWT $ pip install PyJWT - Question:33198428
# jsonify so we can return the information
# uuid to generate a random public id
# install SQLAlchemy using pip: $ pip install -U Flask-SQLAlchemy
# install JWT using pip: $ pip install PyJWT
# password_hash for -> once we put the passwords in the database we need it to be hashed

app = Flask(__name__)

# todo: track modifications part was added to suppress warnings... if it breaks anything just remove it
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisissecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
# DB URI /// - 3 slashes for URI means a relative path - within the project
# DB URI //// - 4 slashes -- it's an absolute path ex: mnt/c/Users/thoshi/Documents/api_example/todo.db

# instantiate SQLAlchemy
db = SQLAlchemy(app)





# class for user table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)


# we don't need a public id for each to-do. we can add if we want
# we can also add a foreign key for to-do if we want

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer)


# we need a public key for each chat conversation
# TODO: add foreign key
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    user_sentence = db.Column(db.String(200))
    chatbot_sentence = db.Column(db.String(200))
    user_emotion = db.Column(db.String(10))
    user_id = db.Column(db.Integer)


class Emotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    user_input = db.Column(db.String(200))
    user_emotion = db.Column(db.String(10))
    user_id = db.Column(db.Integer)


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_name = db.Column(db.String(50), unique=True)
    song_link = db.Column(db.String(1000))


class Ratings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, ForeignKey('songs.id'))
    user_id = db.Column(db.Integer, ForeignKey('user.id'))
    ratings = db.Column(db.Integer)


# class Name on Emotions
class_names = ['joy', 'fear', 'anger', 'sadness', 'neutral']


# ============== decorator for header
# token_required takes in the function that gets decorated
# the inner decorated function gets passed in the positional arguments and the keyword arguments
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # create an empty token
        token = None
        # if there is a header called 'x-access-token'
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        # token is there
        try:
            # not-working-code: jwt.decode(token, app.config['SECRET_KEY'])
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        # token is valid and we also have a user
        # pass the user object to the route
        return f(current_user, *args, **kwargs)

    # return the decorated function
    return decorated


# ============== create database using python shell ==============
# go to shell and type $ python
# $ from app import db
# $ db.create_all()
# to create the databases. a file called 'todo.db' will be created in the specified file path
# exit python shell using # exit()

# ============== check tables using sqlite3 ==============
# to install sqlite refer to the second answer(by-taimur alam):
# https://stackoverflow.com/questions/4578231/error-while-accessing-sqlite3-shell-from-django-application
# go to shell and type $ sqlite3 todo.db
# and view the tables $ .tables
# exit sqlite3 $ .exit
# if you had data you can query from there itself

# we use a public ID because. if we put the public ID in a token. we can see it if we decode the token. And we don't
# want the ID to match up exactly with the sequential ID's in the database, because then someone would know how many
# users there are in the database and simply supply the next number or the previous number. To make it harder to
# figure out the users we use the public id. we will generate the public id from a library called uid

# boiler place route for reference
# @app.route('/')
# def hello_world():
#     return 'Hello World!'

# use routes will only be accessible by admin users
# admin users can see other users, create a new user and delete users

# ============== user routes ============== get all users
#  todo: add decorator for all route methods when adding token
#  required decorator.. we also need to pass in the current user - because we are passing it to the function that
#  gets decorated
@app.route('/user', methods=['GET'])
@token_required
def get_all_users(current_user):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function!'})

    # query users table
    users = User.query.all()
    output = []
    for user in users:
        user_data = {'public_id': user.public_id, 'name': user.name, 'password': user.password, 'admin': user.admin}
        output.append(user_data)

    return jsonify({'users': output})


# get one user
# todo: current user get's passing in first... public_id will be a positional argument... i.e: *args
@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user, public_id):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function!'})

    user = User.query.filter_by(public_id=public_id).first()
    # no user found
    if not user:
        return jsonify({'message': 'No user found!'})

    # if user found
    user_data = {'public_id': user.public_id, 'name': user.name, 'password': user.password, 'admin': user.admin}

    return jsonify({'user': user_data})


# create user
@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function!'})

    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    new_user = User(public_id=str(uuid.uuid4()), name=data['name'], password=hashed_password, admin=False)

    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'New user created!'})


# promote user to an admin
@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def promote_user(current_user, public_id):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function!'})

    user = User.query.filter_by(public_id=public_id).first()
    # no user found
    if not user:
        return jsonify({'message': 'No user found!'})

    # user found
    user.admin = True
    db.session.commit()
    return jsonify({'message': 'The user has been promoted!'})


# delete user
@app.route('/user/<public_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, public_id):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function!'})

    user = User.query.filter_by(public_id=public_id).first()
    # no user found
    if not user:
        return jsonify({'message': 'No user found!'})

    # user found
    db.session.delete(user)
    db.session.commit()
    return {'message': 'user has been deleted! '}


# ============== authentication routes ==============
# this route will allow us to take the username and password for a user. enter it using
# http basic authentication. in return get a token. the front end can use that token for future stuff
# the token will expire after some time. when that token is put in the header of all subsequent requests...
# we know that the user is authenticated

@app.route('/login')
def login():
    auth = request.authorization

    # if no authentication information is passed in
    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify - missing authentication', 401,
                             {'WWW-Authenticate': 'Basic realm="Login required!"'})

    # authentication info is passed in
    # todo: username should be unique
    user = User.query.filter_by(name=auth.username).first()

    # no such user found
    if not user:
        return make_response('Could not verify - no such user', 401,
                             {'WWW-Authenticate': 'Basic realm="Login required!"'})

    # user exists in the database
    # check for password
    # password matches
    if check_password_hash(user.password, auth.password):
        # an expiration is a unix utc timestamp in python we can add a time delta to utc now. now the token is active
        # for only 30 minutes todo: let the user the option to stay signed in for a few days... and change the time
        #  delta app.config['SECRET_KEY'] will be used to encode the token token = jwt.encode( {'public_id':
        #  user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},app.config[
        #  'SECRET_KEY'])
        token = jwt.encode(
            {'public_id': user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=300)},
            app.config['SECRET_KEY'], algorithm="HS256")
        # to decode jwt token  # decode token data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        # not-working:   # return jsonify({'token': token.decode('UTF-8')})
        # for reference: # return jsonify({'token': data}) # got this from youtube comment - Rafael Gramoschi
        return jsonify({'token': token})
    # if password doesn't match
    return make_response('Could not verify - incorrect password', 401,
                         {'WWW-Authenticate': 'Basic realm="Login required!"'})


# ============== to-do items routes ==============
@app.route('/todo', methods=['GET'])
@token_required
def get_all_todos(current_user):
    # query the database to find all to-do's that belong to the current user
    todos = Todo.query.filter_by(user_id=current_user.id).all()

    # an array to hold all the dictionaries
    output = []
    # inserting each to-do into it's own dictionary
    for todo in todos:
        todo_data = {'id': todo.id, 'text': todo.text, 'complete': todo.complete}
        output.append(todo_data)

    return jsonify({'todos': output})


@app.route('/todo/<todo_id>', methods=['GET'])
@token_required
def get_one_todo(current_user, todo_id):
    # todo: this way no user can't see someone else's todo
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    # to-do not found
    if not todo:
        return jsonify({'message': 'No todo found!'})

    # to-do was found
    todo_data = {'id': todo.id, 'text': todo.text, 'complete': todo.complete}
    return jsonify(todo_data)


@app.route('/todo', methods=['POST'])
@token_required
def create_todo(current_user):
    data = request.get_json()

    # we get the user_id from the web token
    new_todo = Todo(text=data['text'], complete=False, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()
    return jsonify({'message': 'Todo Created!'})


@app.route('/todo/<todo_id>', methods=['PUT'])
@token_required
def complete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    # to-do not found
    if not todo:
        return jsonify({'message': 'No todo found!'})

    todo.complete = True
    db.session.commit()
    return jsonify({'message': 'Todo item set to complete'})


@app.route('/todo/<todo_id>', methods=['DELETE'])
@token_required
def delete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()

    # to-do not found
    if not todo:
        return jsonify({'message': 'No todo found!'})

    db.session.delete(todo)
    # a commit will save the change in the database
    db.session.commit()
    return jsonify({'message': 'Todo item deleted!'})


# ============================= Normal User CHAT ROUTES =============================
# TODO: add validation and error handling code
# json request body structure
# { 'userInput' : 'hi, How's the weather today?' }
@app.route('/chat', methods=['POST'])
@token_required
def create_chat_conversation(current_user):
    # admin users cannot have chats
    if current_user.admin:
        return jsonify({'message': 'Admin users cannot create chat conversations!'})

    client_data = request.get_json(force=True)
    # Encoding json
    encodedRequest = ([client_data['userInput']])

    user_emotion = (class_names[np.argmax(preProcessEmotionModel(encodedRequest))])

    brain_shop_payload = {
        'bid': '155151',
        'key': 'tKJeOa4WLS84Eyee',
        'uid': current_user.id,
        'msg': client_data['userInput']
    }
    brain_shop_endpoint = 'http://api.brainshop.ai/get?'

    try:
        # GET request to brain API
        chatbot_request = requests.get(brain_shop_endpoint, params=brain_shop_payload)
        brain_data = chatbot_request.json()
        chatbot_sentence = brain_data['cnt']

    except:
        return jsonify({'error': 'Brainshop service unavailable'}), 503

    # Saving data
    new_conversation = Chat(public_id=str(uuid.uuid4()), user_sentence=client_data['userInput'],
                            chatbot_sentence=chatbot_sentence, user_id=current_user.id, user_emotion=user_emotion)
    db.session.add(new_conversation)
    db.session.commit()

    return jsonify(
        {'chatBotResponse': chatbot_sentence,
         'userInputEmotion': user_emotion
         })


@app.route('/chat', methods=['GET'])
@token_required
def get_all_chat_conversations(current_user):
    # admin users cannot have chats
    if current_user.admin:
        return jsonify({'message': 'Admin users cannot read user chat conversations!'})

    conversations = Chat.query.filter_by(user_id=current_user.id).all()

    # an array to hold all the dictionaries
    output = []
    # inserting each conversation in it's own dictionary
    for conversation in conversations:
        conversation_data = {'public_id': conversation.public_id, 'user_sentence': conversation.user_sentence,
                             'chatbot_sentence': conversation.chatbot_sentence,
                             'user_emotion': conversation.user_emotion}
        output.append(conversation_data)
    return jsonify({'conversations': output})


# get chats sequential
# sequential will send 10 at a time
@app.route('/chat/sequential/<number>', methods=['GET'])
@token_required
def get_chat_sequential(current_user, number):
    # admin users cannot have chats
    if current_user.admin:
        return jsonify({'message': 'Admin users do not have a sequential chat option!'})

    # limit only send the fist (5) fetched queries. offset offsets the request by the
    # example: if I there are 20 chats I can give requests,
    # 0 - get first 5 (/chat/sequential/0)
    # 1 - get 6-10, 2 - get 11-15, 3 - get 16-20
    conversations = Chat.query.filter_by(user_id=current_user.id).limit(5).offset(number)

    # an array to hold selected page size
    output = []
    # inserting each conversation in it's own dictionary
    for conversation in conversations:
        conversation_data = {'public_id': conversation.public_id, 'user_sentence': conversation.user_sentence,
                             'chatbot_sentence': conversation.chatbot_sentence,
                             'user_emotion': conversation.user_emotion}
        output.append(conversation_data)
    return jsonify({'conversations': output})


@app.route('/chat/<user_public_id>', methods=['DELETE'])
@token_required
def admin_delete_user_chat_conversations(current_user, user_public_id):
    # normal users cannot delete other user's chats
    if not current_user.admin:
        return jsonify({'message': 'This delete route is not for Admin users user route /chat/[user_id]'})

    user = User.query.filter_by(public_id=user_public_id).first()
    if not user:
        return jsonify({'message': 'no such user'})

    userId = user.id

    deleted = 0
    while True:
        conversation = Chat.query.filter_by(user_id=userId).first()
        # no conversation in iteration
        if not conversation:
            break

        db.session.delete(conversation)
        deleted += 1

    if deleted == 0:
        return jsonify({'message': 'No conversations of user {} deleted!'.format(user_public_id)})

    db.session.commit()
    return jsonify({'message': 'chat data of user {} successfully deleted'.format(user_public_id)})


@app.route('/chat', methods=['DELETE'])
@token_required
def user_delete_all_chat_conversations(current_user):
    # admin users cannot use this route
    if current_user.admin:
        return jsonify({'message': 'This delete route is not for Admin users user route /chat/[user_id]'})

    deleted = 0
    while True:
        conversation = Chat.query.filter_by(user_id=current_user.id).first()
        # no conversation in iteration
        if not conversation:
            break

        db.session.delete(conversation)
        deleted += 1

    if deleted == 0:
        return jsonify({'message': 'No conversations to delete!'})

    db.session.commit()
    return jsonify({'message': 'all conversations successfully deleted'})


# ========================== emotion endpoint ============================================
@app.route('/emotions', methods=['GET'])
@token_required
def get_all_chat_emotions(current_user):
    # admin users cannot have chats
    if current_user.admin:
        return jsonify({'message': 'Admin users cannot read user chat conversations!'})

    emotions = Emotion.query.filter_by(user_id=current_user.id).all()

    # an array to hold all the dictionaries
    output = []
    # inserting each to-do into it's own dictionary
    for emotion in emotions:
        emotion_data = {'id': emotion.id, 'public_id': emotion.public_id, 'user_Input': emotion.user_input,
                        'user_emotion': emotion.user_emotion}
        output.append(emotion_data)
    return jsonify({'emotions': output})


@app.route('/emotion', methods=['POST'])
@token_required
def user_get_emotion(current_user):
    if current_user.admin:
        return jsonify({'message': 'This delete route is not for Admin users user route /chat/[user_id]'})

    # Requesting and Encoding jason data
    client_request = request.get_json(force=True)

    # Encoding json
    encodedRequest = ([client_request['userInput']])

    user_emotion = (class_names[np.argmax(preProcessEmotionModel(encodedRequest))])

    # Saving data
    new_emotion = Emotion(public_id=str(uuid.uuid4()), user_input=client_request['userInput'],
                          user_emotion=user_emotion, user_id=current_user.id)
    db.session.add(new_emotion)
    db.session.commit()

    return jsonify({'userInputEmotion': user_emotion}), 200


@app.route('/rating', methods=['POST'])
@token_required
def user_create_song_rating(current_user):
    # admin users cannot use this route
    if current_user.admin:
        return jsonify({'message': 'This delete route is not for Admin users user route /chat/[user_id]'})

    data = request.get_json()

    new_rating = Ratings(song_id=data['song_id'], user_id=current_user.id, ratings=data['rating'])
    db.session.add(new_rating)
    db.session.commit()
    return jsonify({'message': 'Rating added'})


@app.route('/emotions', methods=['DELETE'])
@token_required
def user_delete_all_emotions(current_user):
    # admin users cannot use this route
    if current_user.admin:
        return jsonify({'message': 'This delete route is not for Admin users user route /chat/[user_id]'})

    deleted = 0
    while True:
        emotion_query = Emotion.query.filter_by(user_id=current_user.id).first()
        # no emotion in iteration
        if not emotion_query:
            break

        db.session.delete(emotion_query)
        deleted += 1

    if deleted == 0:
        return jsonify({'message': 'No emotions to delete!'})

    db.session.commit()
    return jsonify({'message': 'all emotions were successfully deleted'})


# ========================== quotes endpoint ============================================
@app.route('/quotes', methods=['GET'])
@token_required
def user_get_quote(current_user):
    # admin users cannot have chats
    if current_user.admin:
        return jsonify({'message': 'Admin users cannot use quotes!'})

    quotes_endpoint = 'https://quotes.rest/qod?category=inspire'
    api_token = "25632gadhgahs6276712"
    headers = {'content-type': 'application/json',
               'X-TheySaidSo-Api-Secret': format(api_token)}

    try:
        # GET request to quotes API
        response = requests.get(quotes_endpoint, headers=headers)
    except:
        return jsonify({'error': 'Quote service unavailable'}), 503

    quote = response.json()['contents']['quotes'][0]['quote']
    author = response.json()['contents']['quotes'][0]['author']

    return jsonify({'quotes': quote, 'author': author})


# ========================== Music endpoint ============================================
@app.route('/add-music', methods=['POST'])
@token_required
def add_music(current_user):
    # allowing only admin user to perform an action
    if not current_user.admin:
        return jsonify({'message': 'You do not have the permission to perform that function!'})

    data = request.get_json()
    new_song = Songs(song_name=data['song_name'], song_link=data['song_link'])
    db.session.add(new_song)
    db.session.commit()
    return jsonify({'message': 'New music added!'})


# @app.route('/recommend-music', methods=['GET'])
# @token_required
# def recommend_music(current_user):
#     user = User.query.all()
#     ratings = Ratings.query.all()
#     print(ratings)
#     return jsonify({'musics': "Terminal"})


if __name__ == '__main__':
    app.run(debug=True)
