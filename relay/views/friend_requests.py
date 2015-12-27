# -*- coding: utf-8 -*-
import logging 

from flask import request

from relay import app
from relay.decorators import jsonify

from relay.models.friends import add_friend_request
from relay.models.friends import confirm_friend_request
from relay.models.friends import get_friendship
from relay.models.friends import get_friend_request


@app.route('/friend_requests', methods=['POST'])
@jsonify
def post_friend_request():
  success = False
  recipient, sender = request.form['recipient'], request.form['sender']

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
    friend_request = send_friend_request(sender, recipient)
    success = friend_request is not None

  return {'success': success}


@app.route('/friend_requests/accept', methods=['POST'])
@jsonify
def post_friends():
  result = False
  sender, recipient = request.form['sender'], request.form['recipient']
  # we need an existing friend request
  existing_request = get_friend_request(sender, recipient)
  if existing_request:
    result = confirm_friend_request(existing_request)
  return {'success': result}
