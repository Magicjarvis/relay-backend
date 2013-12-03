""" main.py is the top level script.
"""

import os
import sys

# sys.path includes 'server/lib' due to appengine_config.py
from flask import Flask, request
from decorators import jsonify
from models import User, UserIndex, Relay, RelayIndex, add_friend, add_relay

from google.appengine.ext import ndb

app = Flask(__name__.split('.')[0])


@app.route('/login', methods=['POST'])
@jsonify
def login_or_register():
  user = User(username=request.form['username'], password=request.form['password']).put()
  return {'success': user is not None}

@app.route('/users')
@jsonify
def get_user():
  return [user.username for user in User.query().iter()]

@app.route('/users/<user_id>/friends')
@jsonify
def get_user_friends(user_id):
  user = User.query().filter(User.username == user_id).get()
  if user is not None:
    user_index = UserIndex.query(ancestor=user.key).get()
    return user_index.friends if user_index is not None else []
  return "Invalid User"

@app.route('/users/<user_id>/friend_requests')
@jsonify
def get_pending_friends(user_id):
  user = User.query().filter(User.username == user_id).get()
  if user is not None:
    friends_model = UserIndex.query(ancestor=user.key).get()
    user_friends_names = friends_model.friends if friends_model is not None else []
    qo = ndb.QueryOptions(keys_only=True)
    friender_keys = UserIndex.query().filter(UserIndex.friends == user.username).iter(options=qo)
    friender_usernames = [key.parent().get().username for key in friender_keys]
    return list(set(friender_usernames) - set(user_friends_names))

  return "Invalid User"

@app.route('/friends', methods=['POST'])
@jsonify
def post_friends():
  result = add_friend(request.form['sender'], request.form['recipient'])
  return {'success': result}

def get_relays(relay_id):
  if relay_id is not None:
    return str(ndb.Key(Relay, relay_id))
  else:
    foo = []
    for relay in Relay.query().iter():
      relay_index = RelayIndex.query(ancestor=relay.key).get()
      recipients = relay_index.recipients if relay_index is not None else []
      foo.append((relay.sender, relay.link, recipients))
    return foo
      
@app.route('/relays', methods=['GET', 'POST'])
@app.route('/relays/<relay_id>')
@jsonify
def reelay(relay_id=None):
  if request.method == 'GET':
    return get_relays(relay_id)
  elif request.method == 'POST':
    result = add_relay(request.form['sender'], request.form['link'], request.form['recipients'])
    return {'success': result}

@app.route('/relays/from/<user_id>')
@jsonify
def get_relays_from_user(user_id=None):
  if user_id is not None:
    relay_items = Relay.query().filter(Relay.sender == user_id).iter()
    foo = []
    for link in relay_items:
      recipients = [recipient.recipients for recipient in RelayIndex.query(ancestor=link.key).iter()]
      foo.append((link.link, recipients))
    return map(str, foo)
  else:
    return "No user_id provided"
  
@app.route('/relays/to/<user_id>')
@jsonify
def get_relay_to_user(user_id=None):
  if user_id is not None:
    qo = ndb.QueryOptions(keys_only=True)
    indexes = RelayIndex.query().filter(RelayIndex.recipients == user_id).iter(options=qo)
    relays = [key.parent().get() for key in indexes]
    return [(r.sender, r.link) for r in relays]
  else:
    return "No user_id provided"

