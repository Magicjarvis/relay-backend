import logging
import flask
from flask import json, Response, request
from functools import wraps
from util import sanitize_username

from google.appengine.ext import ndb
from models.users import User


def session_required(f):
  @wraps(f)
  def grab_user_for_session(*args, **kwargs):
    session = request.headers.get('Authorization')
    user = None
    if session:
      user = User.query().filter(User.session_tokens == session).get()
      logging.info("Authenticated user: " + str(user.key.id() if user else None))
    return f(*args, user=user, **kwargs)
  return grab_user_for_session

def jsonify(f):
  @wraps(f)
  def as_json(*args, **kwargs):
    return flask.jsonify(f(*args, **kwargs))
  return as_json

def sanitize_user(f):
  @wraps(f)
  def check_valid_user(*args, **kwargs):
    user_id = kwargs.get('user_id')
    if user_id is None:
      return "No user id provided"
    user_id = sanitize_username(user_id)
    kwargs['user_id'] = user_id
    return f(*args, **kwargs)
  return check_valid_user

