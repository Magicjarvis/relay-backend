# -*- coding: utf-8 -*-
from google.appengine.ext import ndb

from relay.util import sanitize_username
from relay.auth import hash_password


def get_user(username):
  return User.get_by_id(username)


def get_usernames():
  """Dumb helper for /users."""
  return [user.key.id() for user in User.query().iter()]


def add_user(username, password, email, gcm_id=None, session_token=None):
  username = sanitize_username(username)
  gcm_ids = [gcm_id] if gcm_id else []
  hashed_password = hash_password(password)
  new_user = User(
    id=username,
    password=hashed_password,
    email=email,
    gcm_ids=gcm_ids,
    session_token=session_token
  ).put()
  return new_user is not None


class User(ndb.Model):
  """Models a user."""
  password = ndb.StringProperty(required=True)
  email = ndb.StringProperty()

  session_token = ndb.StringProperty(indexed=True)
  gcm_ids = ndb.StringProperty(repeated=True)
