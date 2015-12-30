# -*- coding: utf-8 -*-
from relay import app
from relay.decorators import jsonify
from relay.decorators import sanitize_user

from relay.models.friends import get_user_friends
from relay.models.friends import get_user_friend_requests
from relay.models.users import get_user
from relay.models.users import get_usernames


@app.route('/users')
@jsonify
def get_all_users_endpoint():
  return {'users': get_usernames()}


@app.route('/users/<user_id>/friends')
@jsonify
@sanitize_user
def user_friends(user_id):
  user = get_user(user_id)
  return {
    'friends': get_user_friends(user_id)
  } if user else {}
  

@app.route('/users/<user_id>/friend_requests')
@jsonify
@sanitize_user
def pending_friends(user_id):
  user = get_user(user_id)
  return {
    'friend_requests': get_user_friend_requests(user_id)
  } if user else {}
