# -*- coding: utf-8 -*-
from google.appengine.ext import ndb


@ndb.transactional(xg=True)
def add_friend(user, other_user):
  Friendship(user=user, other_user=other_user).put()
  Friendship(user=other_user, other_user=user).put()
  return True


class Friendship(ndb.Model):
  user = ndb.StringProperty(indexed=True, required=True)
  other_user = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)


class FriendRequest(ndb.Model):
  recipient = ndb.StringProperty(indexed=True, required=True)
  sender = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)
