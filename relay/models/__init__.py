# -*- coding: utf-8 -*-
from google.appengine.ext import ndb

from relays import Relay
from relays import SentRelay
from friends import FriendRequest
from friends import Friendship
from users import User


def delete_db(drop_users=False):
  if drop_users:
    ndb.delete_multi(User.query().fetch(keys_only=True))
  ndb.delete_multi(Relay.query().fetch(keys_only=True))
  ndb.delete_multi(SentRelay.query().fetch(keys_only=True))
  ndb.delete_multi(Friendship.query().fetch(keys_only=True))
  ndb.delete_multi(FriendRequest.query().fetch(keys_only=True))
