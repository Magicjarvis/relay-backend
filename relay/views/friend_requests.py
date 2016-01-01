# -*- coding: utf-8 -*-
import logging 

from flask import request

from relay import app
from relay.decorators import jsonify

from relay.models.friends import confirm_friend_request
from relay.models.friends import get_friendship
from relay.models.friends import get_friend_request

from relay.util import sanitize_username

from google.appengine.api import taskqueue


@app.route('/friend_requests', methods=['POST'])
@jsonify
def post_friend_request():
  success = False
  recipient = sanitize_username(request.form['recipient'])
  sender = sanitize_username(request.form['sender'])

  # existing friendship?
  if get_friendship(sender, recipient):
    return {'success': False}
  
  # maybe you're requesting someone who's requested you
  opposite_request = get_friend_request(recipient, sender)
  if opposite_request:
    logging.info('User has already been requested. Confirming friend request')
    return {'success': confirm_friend_request(opposite_request)}

  existing_request = get_friend_request(recipient, sender)
  if recipient != sender and not existing_request:
    task = taskqueue.add(
      url='/post_friend_request_queue',
      params={
        'sender': sender,
        'recipient': recipient,
      }
    )
    success = task.was_enqueued

  return {'success': success}


@app.route('/friend_requests/accept', methods=['POST'])
@jsonify
def post_friends():
  result = False
  recipient = sanitize_username(request.form['recipient'])
  sender = sanitize_username(request.form['sender'])
  # we need an existing friend request
  existing_request = get_friend_request(sender, recipient)
  if existing_request:
    result = confirm_friend_request(existing_request)
  return {'success': result}
