# -*- coding: utf-8 -*-
from relay import app
from relay.decorators import jsonify

from relay.models import User, Friendship, FriendRequest

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
  

@app.route('/users/<user_id>/friend_requests')
@jsonify
def get_pending_friends(user_id):
  user = get_user(user_id)
  friend_requests = FriendRequest.query().filter(FriendRequest.recipient == user.key.id(), FriendRequest.active == True).iter()
  return {'friend_requests': [friend_request.sender for friend_request in friend_requests]}
