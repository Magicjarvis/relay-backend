import flask
from flask import json, Response
from functools import wraps

from google.appengine.ext import ndb
from models import User 

def jsonify(f):
  @wraps(f)
  def as_json(*args, **kwargs):
    return flask.jsonify(f(*args, **kwargs))
  return as_json

def validate_user(f):
  @wraps(f)
  def check_valid_user(*args, **kwargs):
    user_id = kwargs.get('user_id')
    if user_id is None:
      return "No user id provided"
    qo = ndb.QueryOptions(keys_only=True)
    user = User.get_by_id(kwargs['user_id'], options=qo)
    if user is None:
      return "Invalid User"
    return f(*args, **kwargs)
  return check_valid_user
