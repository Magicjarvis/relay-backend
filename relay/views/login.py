# -*- coding: utf-8 -*-
from flask import request

from relay import app
from relay.decorators import jsonify
from relay.decorators import validate_user

from relay.models import add_user
from relay.models import get_user

from relay.auth import generate_session_id
from relay.auth import verify_password 

# todo: add logout, should sessions->users? we always have the user right?
@app.route('/login', methods=['POST'])
@jsonify
def login_user():
  username = request.form['username']
  password = request.form['password']
  gcm_id = request.form.get('gcm_id')
  user = get_user(username)
  session_token = None
  if user and verify_password(password, user.password):
    session_token = generate_session_id()
    user.session_token = session_token
    if gcm_id and gcm_id not in user.gcm_ids:
      user.gcm_ids.append(gcm_id) 
    user.put()
    result = session_token
  return {'session': session_token}


@app.route('/register', methods=['POST'])
@jsonify
def register_user():
  username = request.form['username']
  password = request.form['password']
  email = request.form['email']
  gcm_id = request.form.get('gcm_id')
  user = get_user(username)
  result = None
  if not user:
    session_token=generate_session_id()
    new_user = add_user(
      username,
      password,
      email,
      gcm_id=gcm_id,
      session_token=session_token
    )
    if new_user:
      result = session_token
  return {'session': result}


@app.route('/unregister', methods=['POST'])
@jsonify
def unregister_gcm():
  username = sanitize_username(request.form['username'])
  gcm_id = request.form['gcm_id']
  result = True
  # unregister the gcm_id
  user = get_user(username)
  if user:
    if gcm_id in user.gcm_ids:
      user.gcm_ids.remove(gcm_id)
      user.gcm_ids = list(set(user.gcm_ids))
      user.put()
  else:
    result = False
  return {'success': result}
