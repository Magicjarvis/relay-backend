# -*- coding: utf-8 -*-

""" main.py is the top level script.
"""

import base64
import os
import sys
import logging

# sys.path includes 'server/lib' due to appengine_config.py
from flask import Flask, request
from decorators import jsonify, validate_user
from models import User, Friendship, Relay, SentRelay, RelayIndex, FriendRequest, add_friend, add_relay, get_relays, delete_db
from gae_python_gcm.gcm import GCMMessage, GCMConnection
from util import extract_url, sanitize_username

from Crypto import Random
from passlib.hash import sha256_crypt

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

app = Flask(__name__.split('.')[0])


def get_user(username):
  return User.get_by_id(username)

def generate_session_id():
    return base64.b64encode(Random.get_random_bytes(16))

def send_push_notification(sender, recipients, title):
  android_payload = {'sender': sender, 'title': title}
  #change the way you do this. get the relay object out of that other method.
  # just return metadata, that would be cool
  # TODO
  success = True
  for recipient in recipients.split(','):
    recipient_user = get_user(recipient)

    if recipient_user and len(recipient_user.gcm_ids):
      gcm_message = GCMMessage(recipient_user.gcm_ids, android_payload)
      gcm_conn = GCMConnection()
      gcm_conn.notify_device(gcm_message)
    else:
      success = False
  return success

def add_user(username, password, email, gcm_id=None, session_token=None):
  username = sanitize_username(username)
  gcm_ids = [gcm_id] if gcm_id else []
  hashed_password = sha256_crypt.encrypt(password)
  new_user = User(
    id=username,
    password=hashed_password,
    email=email,
    gcm_ids=gcm_ids,
    session_token=session_token
  ).put()
  return new_user is not None

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

@app.route('/foob')
@jsonify
def test_latecy():
  return {'foo': str([x for x in User.query().filter(User.email == 'magicjarvis@gmail.com').iter()]),
    'bar': str([y for y in RelayIndex.query().filter('russell' == RelayIndex.recipients).iter()])
      }

@app.route('/test/<user_id>')
@jsonify
def test_latency(user_id):
  return {'Relays': [str(r) for r in Relay.query().iter()],
      'SentRelays': [str(sr) for sr in SentRelay.query().iter()],
      'RelayIndex': [str(ri) for ri in RelayIndex.query().iter()],
      'UserID': sanitize_username(user_id),
          'success': True}
  
# todo: add logout, should sessions->users? we always have the user right?
@app.route('/login', methods=['POST'])
@jsonify
def login():
  username = request.form['username']
  password = request.form['password']
  gcm_id = request.form.get('gcm_id')
  user = get_user(username)
  session_token = None
  if user and sha256_crypt.verify(password, user.password):
    session_token = generate_session_id()
    user.session_token = session_token
    if gcm_id and gcm_id not in user.gcm_ids:
      user.gcm_ids.append(gcm_id) 
    user.put()
    result = session_token
  return {'session': session_token}


@app.route('/register', methods=['POST'])
@jsonify
def register():
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


@app.route('/users')
@jsonify
def get_all_users_endpoint():
  return {'users': [user.key.id() for user in User.query().iter()]}

@app.route('/users/<user_id>/friends')
@jsonify
def get_user_friends(user_id):
  user = get_user(user_id)
  friendships = Friendship.query().filter(Friendship.user == user_id).iter()
  return {'friends': [friendship.other_user for friendship in friendships]}
  

def confirm_friend_request(friend_request):
  friend_request.active = False
  friend_request.put()
  return add_friend(friend_request.sender, friend_request.recipient)


@app.route('/friend_requests', methods=['POST'])
@jsonify
def post_friend_request():
  success = False
  recipient, sender = request.form['recipient'], request.form['sender']

  existing_friendship = Friendship.query().filter(Friendship.user == sender).get()
  if existing_friendship:
    return {'success': False}
  
  # maybe you're requesting someone who's requested you
  opposite_request = FriendRequest.query().filter(FriendRequest.sender==recipient, FriendRequest.recipient==sender).get()
  logging.info('the value of opposite_request %s'%(str(opposite_request)))
  if opposite_request:
    logging.info('opposite request is real so we confirm the request')
    return {'success': confirm_friend_request(opposite_request)}

  existing = FriendRequest.query().filter(FriendRequest.sender==sender, FriendRequest.recipient==recipient).get()
  logging.info('the value of existing %s'%(str(existing)))
  if recipient != sender and not existing:
    logging.info('we are creating a friend request')
    friend_request = FriendRequest(recipient=recipient, sender=sender).put()
    success = friend_request is not None

  return {'success': success}

@app.route('/users/<user_id>/friend_requests')
@jsonify
def get_pending_friends(user_id):
  user = get_user(user_id)
  friend_requests = FriendRequest.query().filter(FriendRequest.recipient == user.key.id(), FriendRequest.active == True).iter()
  return {'friend_requests': [friend_request.sender for friend_request in friend_requests]}

@app.route('/friend_requests/accept', methods=['POST'])
@jsonify
def post_friends():
  result = False
  sender, recipient = request.form['sender'], request.form['recipient']
  # we need an existing friend request
  existing = FriendRequest.query().filter(
    FriendRequest.sender == sender,
    FriendRequest.recipient == recipient,
    FriendRequest.active == True
  ).get()
  if existing:
    result = confirm_friend_request(existing)
  return {'success': result}


@app.route('/relays', methods=['GET', 'POST'])
@app.route('/relays/<int:sent_relay_id>')
@jsonify
def reelay(sent_relay_id=None):
  if request.method == 'GET':
    offset = int(request.args.get('offset', 0))
    return {'relays': get_relays(sent_relay_id, offset)}
  elif request.method == 'POST':
    task = taskqueue.add(
      url='/post_relay_queue',
      params={
        'url': request.form['url'],
        'sender': request.form['sender'],
        'recipients': request.form['recipients'],
      }
    )
    return {'success': task.was_enqueued}


@app.route('/post_relay_queue', methods=['POST'])
@jsonify
def post_relay():
  url = extract_url(request.form['url'])
  sender = request.form['sender']
  recipients = request.form['recipients']
  if not url:
    return {'success': False}
  relay = add_relay(sender, url, recipients)
  result = relay is not None
  if relay:
    send_push_notification(sender, recipients, relay.title)
  return {'success': result}


@app.route('/relays/delete', methods=['POST'])
@jsonify
def delete_relay():
  # TODO make this a delete, bitch
  # TODO validate this. insecure as fuh
  relay_id = int(request.form['relay_id'])
  user_id = sanitize_username(request.form['user_id'])
  sent_relay = SentRelay.get_by_id(relay_id) 
  if sent_relay.saved:
    sent_relay.key.delete()
    return {'success': True}

  relay_index = RelayIndex.query(ancestor=sent_relay.key).get()
  user_idx = relay_index.recipients.index(user_id) if user_id in relay_index.recipients else -1
  result = None
  if user_idx != -1:
      result = relay_index.recipients.pop(user_idx)
      relay_index.put()
  return {'success': result is not None}

def make_relay_map(sent_relay):
  relay = sent_relay.relay.get()
  return {
      'id': sent_relay.key.id(),
      'sender': sent_relay.sender,
      'title': relay.title,
      'description': relay.description,
      'image': relay.image,
      'favicon': relay.favicon,
      'site': relay.site,
      'url': relay.key.id(),
      'kind': relay.kind
  }

@app.route('/relays/from/<user_id>')
@jsonify
@validate_user
def get_relays_from_user(user_id=None):
  offset = int(request.args.get('offset', 0))
  qo = ndb.QueryOptions(limit=10, offset=offset)
  sent_relay_items = SentRelay.query().order(-SentRelay.timestamp).filter(SentRelay.sender == user_id).filter(SentRelay.saved == False).iter(options=qo)
  sent_relays = []
  for sent_relay_item in sent_relay_items:
    relay_index = RelayIndex.query(ancestor=sent_relay_item.key).get()
    item_map = make_relay_map(sent_relay_item)
    item_map.pop('sender', None)
    if user_id in relay_index.recipients:
      continue
    item_map['recipients'] = sent_relay_item.to
    sent_relays.append(item_map)
  return {'relays': sent_relays}
  
@app.route('/clear')
@jsonify
def clear_out_db():
  delete_db()
  return {}

def get_relays_for_recipient(user_id, offset):
  qo = ndb.QueryOptions(keys_only=True, limit=10, offset=offset)
  indexes = RelayIndex.query().filter(RelayIndex.recipients == user_id).order(-RelayIndex.timestamp).iter(options=qo)
  result = [key.parent().get() for key in indexes]
  logging.info('get_relay_for_recipient(%s) -> %s'%(user_id, str(result)))
  return result

@app.route('/relays/saved/<user_id>')
@jsonify
@validate_user
def get_saved_relays(user_id=None):
  offset = int(request.args.get('offset', 0))
  qo = ndb.QueryOptions(limit=10, offset=offset)
  saved_relay_items = SentRelay.query().order(-SentRelay.timestamp).filter(SentRelay.sender == user_id).filter(SentRelay.saved == True).iter(options=qo)
  return {
    'relays' : map(make_relay_map, saved_relay_items)
  }

@app.route('/relays/to/<user_id>')
@jsonify
@validate_user
def get_relay_to_user(user_id=None):
  offset = int(request.args.get('offset', 0))
  relays = get_relays_for_recipient(user_id, offset)
  return {'relays' :
    [
      make_relay_map(r) for r in relays
      if sanitize_username(r.sender) != sanitize_username(user_id)
    ]
  } # sanitize for sanity, probably dont need
