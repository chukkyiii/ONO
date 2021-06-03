from logging import debug
from flask import Flask, render_template, request, redirect, url_for
from flask_login import current_user, login_user, login_required, logout_user, LoginManager
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.errors import DuplicateKeyError
from db import get_user, save_user, save_message, timeformat, message_collection
from datetime import datetime
import re 

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "O!N@O£"
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@app.route('/')
def home():

    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if user and user.check_password(password_input):
            login_user(user)
            return redirect(url_for('menu'))
        else: 
            message = 'Incorrect Username or Password'
        

    return render_template('index.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_check: bool = re.search('^(?=.{8,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$', username)
        pass_check: bool = re.search('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,10}$', password)
        if user_check and pass_check:
            try:
                save_user(username, email, password)
                return redirect(url_for('login'))
            except DuplicateKeyError:
                message = 'User already exists!'
        else: 
            message = 'username or password needs to be secure!'
    return render_template('signup.html', message=message)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/menu')
def menu():
    username = request.form.get('username') #NOTE: current_error: command not allowed -> might relate to form atrribute in index.html 
    return render_template('menu.html', username=username)

@app.route('/chat')
@login_required
def chat():
    room = request.args.get('room')

    messages = [msg for msg in message_collection.find()]
    for index in messages:
        if timeformat(index['time']) >= 24:
            message_collection.delete_one(index) 
        del index['_id']

    if room:
        return render_template('chat.html', room=room, messages=messages, time=datetime.now().strftime('%X'))
    else:
        return redirect('/menu')


@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined room {}".format(
        data['username'], data['room']))
    join_room(data["room"])
    socketio.emit('join_room_annoucement', data, room=data['room'])


@socketio.on('leave_room')
def handle_leave_room_event(data):
    app.logger.info("{} has left the room {}".format(
        data['username'], data['room']))
    leave_room(data['room'])
    socketio.emit('leave_room_annoucement', data, room=data['room'])


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} in room {}: {}".format(
        data['username'], data['room'], data['message']))
    save_message(data['username'], data['room'], data['message'])
    socketio.emit('receive_message', data, room=data['room'])

@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == "__main__":
    print('running...')
    socketio.run(app, debug=True, host="192.168.0.67")
    
