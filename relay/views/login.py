# -*- coding: utf-8 -*-
from flask import request

from relay import app
from relay.decorators import jsonify
from relay.decorators import session_required

from relay.models.users import add_user
from relay.models.users import get_user

from relay.auth import generate_session_id
from relay.auth import verify_password 

from relay.util import sanitize_username


# todo: add logout, should sessions->users? we always have the user right?
@app.route('/login', methods=['POST'])
@jsonify
def login_user():
  username = sanitize_username(request.form['username'])
  password = request.form['password']
  gcm_id = request.form.get('gcm_id')
  user = get_user(username)
  session_token = None
  if user and verify_password(password, user.password):
    session_token = generate_session_id()
    if session_token not in user.session_tokens:
      user.session_tokens.append(session_token)
    if gcm_id and gcm_id not in user.gcm_ids:
      user.gcm_ids.append(gcm_id) 
    user.put()
    result = session_token
  return {'session': session_token}


@app.route('/register', methods=['POST'])
@jsonify
def register_user():
  # we store the name the user registers with as the display name
  # we sanitize a different username to make collisions easier to find
  display_name = request.form['username']
  username = sanitize_username(display_name)

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


@app.route('/logout', methods=['POST'])
@jsonify
@session_required
def logout(user=None):
  if not user:
    return {'success': False}

  # enforce later
  session_token = request.headers.get('Authorization')
  gcm_id = request.form.get('gcm_id')

  _unregister_session(user, session_token)
  _unregister_gcm(user, gcm_id)

  result = user.put()

  return {'success': result is not None}


def _unregister_session(user, session_token):
  if session_token in user.session_tokens:
    user.session_tokens.remove(session_token)
    user.session_tokens = list(set(user.session_tokens))


def _unregister_gcm(user, gcm_id):
  if gcm_id in user.gcm_ids:
    user.gcm_ids.remove(gcm_id)
    user.gcm_ids = list(set(user.gcm_ids))
