""" main.py is the top level script.
"""

import os
import sys

# sys.path includes 'server/lib' due to appengine_config.py
from flask import Flask, request
from decorators import jsonify, validate_user
from models import User, UserIndex, Relay, RelayIndex, add_friend, add_relay, get_relays

from google.appengine.ext import ndb

app = Flask(__name__.split('.')[0])



def add_user(username, password):
  new_user = User(id=username, password=password).put()
  return new_user is not None

@app.route('/login', methods=['POST'])
@jsonify
def login_or_register():
  username, password = request.form['username'], request.form['password']
  result = False
  user = User.get_by_id(username)
  if user is None:
    result = add_user(request.form['username'], request.form['password'])
  else:
    result = user.password == password
  return {'success': result}

@app.route('/users')
@jsonify
def get_user():
  return {'users': [user.key.id() for user in User.query().iter()]}

@app.route('/users/<user_id>/friends')
@jsonify
def get_user_friends(user_id):
  user = User.get_by_id(user_id)
  if user is not None:
    user_index = UserIndex.query(ancestor=user.key).get()
    return user_index.friends if user_index is not None else []
  return {'error': 'Invalid User'}

@app.route('/users/<user_id>/friend_requests')
@jsonify
def get_pending_friends(user_id):
  user = User.get_by_id(user_id)
  if user is not None:
    friends_model = UserIndex.query(ancestor=user.key).get()
    user_friends_names = friends_model.friends if friends_model is not None else []
    qo = ndb.QueryOptions(keys_only=True)
    friender_keys = UserIndex.query().filter(UserIndex.friends == user.key.id()).iter(options=qo)
    friender_usernames = [key.parent().id() for key in friender_keys]
    return {'requests': list(set(friender_usernames) - set(user_friends_names))}
  return {'error': 'Invalid User'}

@app.route('/friends', methods=['POST'])
@jsonify
def post_friends():
  sender, recipient = request.form['sender'], request.form['recipient']
  result = add_friend(sender, recipient) if sender != recipient else False
  return {'success': result}

@app.route('/relays', methods=['GET', 'POST'])
@app.route('/relays/<int:relay_id>')
@jsonify
def reelay(relay_id=None):
  if request.method == 'GET':
    return {'relays': get_relays(relay_id)}
  elif request.method == 'POST':
    result = add_relay(request.form['sender'], request.form['url'], request.form['recipients'])
    return {'success': result}


def make_relay_map(relay):
  return {
      'id': relay.key.id(),
      'sender': relay.sender,
      'title': relay.title,
      'description': relay.description,
      'image': relay.image,
      'favicon': relay.favicon,
      'site': relay.site,
      'url': relay.url,
      'kind': relay.kind
  }

@app.route('/relays/from/<user_id>')
@jsonify
@validate_user
def get_relays_from_user(user_id=None):
  relay_items = Relay.query().order(-Relay.timestamp).filter(Relay.sender == user_id ).filter(Relay.stale == False).iter()
  relays = []
  for relay_item in relay_items:
    relay_index = RelayIndex.query(ancestor=relay_item.key).get()
    item_map = make_relay_map(relay_item)
    item_map.pop('sender', None)
    item_map['recipients'] = relay_index.recipients if relay_index is not None else []
    relays.append(item_map)
  return {'relays': relays}
  

@app.route('/relays/to/<user_id>')
@jsonify
def get_relay_to_user(user_id=None):
  qo = ndb.QueryOptions(keys_only=True)
  indexes = RelayIndex.query().filter(RelayIndex.recipients == user_id).iter(options=qo)
  relays = [key.parent().get() for key in indexes]
  relays.sort(key=lambda x: x.timestamp)
  relays.reverse()
  return {'relays' : [make_relay_map(r) for r in relays if not r.stale]}
