# -*- coding: utf-8 -*-
from google.appengine.ext import ndb


def get_user_friends(user):
  """Returns a user's friends list."""
  return [
    friendship.other_user
    for friendship in Friendship.query().filter(Friendship.user == user).iter()
  ]


def get_user_friend_requests(user):
  """Returns active friend requests for a user."""
  return [
    friend_request.sender
    for friend_request in FriendRequest.query().filter(FriendRequest.recipient == user, FriendRequest.active == True).iter()
  ]


def get_friendship(user, other_user):
  """Returns a Friendship doc."""
  return Friendship.query().filter(
    Friendship.user == user,
    Friendship.other_user == other_user
  ).get()

def get_friend_request(sender, recipient):
  """Returns a FriendRequest doc."""
  return FriendRequest.query().filter(
    FriendRequest.sender==sender,
    FriendRequest.recipient==recipient,
    FriendRequest.active == True
  ).get()


def add_friend_request(sender, recipient):
  # send a push notification here eventually
  return _add_friend_request(sender, recipient)


def _add_friend_request(sender, recipient):
  return FriendRequest(recipient=recipient, sender=sender).put()


@ndb.transactional(xg=True)
def add_friend(user, other_user):
  Friendship(user=user, other_user=other_user).put()
  Friendship(user=other_user, other_user=user).put()
  return True


@ndb.transactional(xg=True)
def confirm_friend_request(friend_request):
  friend_request.active = False
  friend_request.put()
  return add_friend(friend_request.sender, friend_request.recipient)


class Friendship(ndb.Model):
  user = ndb.StringProperty(indexed=True, required=True)
  other_user = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)


class FriendRequest(ndb.Model):
  recipient = ndb.StringProperty(indexed=True, required=True)
  sender = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)
