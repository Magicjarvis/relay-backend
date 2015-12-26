# -*- coding: utf-8 -*-
import logging 

from flask import request

from relay import app
from relay.decorators import jsonify

from relay.models.friends import Friendship
from relay.models.friends import FriendRequest

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
