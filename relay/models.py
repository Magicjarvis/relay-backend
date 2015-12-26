# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
from metadata import scrape as scrape_metadata
from util import sanitize_username
from auth import hash_password
import tldextract

def get_relays_for_recipient(user_id, offset):
  qo = ndb.QueryOptions(limit=10, offset=offset)
  sent_relays_iter = SentRelay.query().filter(
    SentRelay.not_archived == user_id, # people who haven't archived
  ).order(
    -SentRelay.timestamp
  ).iter(options=qo)
  sent_relays = [item for item in sent_relays_iter]
  logging.info('get_relay_for_recipient(%s) -> %s'%(user_id, str(sent_relays)))
  return sent_relays

def get_user(username):
  return User.get_by_id(username)

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

def get_relays(sent_relay_id, offset):
  if sent_relay_id is not None:
    return str(SentRelay.get_by_id(sent_relay_id))

  sent_relays = []
  for sent_relay in SentRelay.query().iter():
    relay = sent_relay.relay.get()
    item = {
        'id':sent_relay.key.id(),
        'sender': sent_relay.sender,
        'recipients': sent_relay.recipients,
        'title': relay.title,
        'description': relay.description,
        'image': relay.image,
        'favicon': relay.favicon,
        'site': relay.site,
        'url': relay.key.id(),
        'kind': relay.kind,
        'archived': sent_relay.archived
    }
    sent_relays.append(item)
  return sent_relays


@ndb.transactional(xg=True)
def add_friend(user, other_user):
  Friendship(user=user, other_user=other_user).put()
  Friendship(user=other_user, other_user=user).put()
  return True


def add_relay_model(url):
  metadata = scrape_metadata(url)
  relay = Relay(**metadata)
  relay.title = relay.title or url
  if (relay.description is not None):
    relay.description = relay.description.strip()
  return relay


@ndb.transactional(xg=True)
def add_relay(sender, url, recipients, save=False):
  relay = Relay.get_by_id(url)
  if recipients:
    recipients = map(sanitize_username, recipients.split(','))
  else:
    recipients = []

  if sender in recipients:
    recipients.remove(sender)

  if relay is None:
    relay = add_relay_model(url)

  relay_key = relay.put()

  sent_relay = SentRelay()
  sent_relay.sender = sanitize_username(sender)
  sent_relay.relay = relay_key
  sent_relay.recipients = recipients # canonical list of recipients
  sent_relay.not_archived = recipients # dirty hack for no != on indexes
  sent_relay.saved = save

  sent_relay_key = sent_relay.put()

  # this should be a sent_relay but whatever
  return relay


def delete_db():
  ndb.delete_multi(Relay.query().fetch(keys_only=True))
  ndb.delete_multi(SentRelay.query().fetch(keys_only=True))
  ndb.delete_multi(Friendship.query().fetch(keys_only=True))
  ndb.delete_multi(FriendRequest.query().fetch(keys_only=True))


class User(ndb.Model):
  """Models a user."""
  password = ndb.StringProperty(required=True)
  email = ndb.StringProperty()

  session_token = ndb.StringProperty(indexed=True)
  gcm_ids = ndb.StringProperty(repeated=True)


class Friendship(ndb.Model):
  user = ndb.StringProperty(indexed=True, required=True)
  other_user = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)


class FriendRequest(ndb.Model):
  recipient = ndb.StringProperty(indexed=True, required=True)
  sender = ndb.StringProperty(indexed=True, required=True)
  active = ndb.BooleanProperty(indexed=True, default=True)


class Relay(ndb.Model):
  """Models a shared (relayed) url."""
  # url is id
  site = ndb.StringProperty()
  favicon = ndb.StringProperty()
  title = ndb.StringProperty()
  image = ndb.StringProperty()
  description = ndb.StringProperty()
  kind = ndb.StringProperty()


class SentRelay(ndb.Model):
  relay = ndb.KeyProperty(kind='Relay')
  sender = ndb.StringProperty(indexed=True, required=True)
  timestamp = ndb.DateTimeProperty(indexed=True, auto_now_add=True)

  saved = ndb.BooleanProperty(indexed=True, default=False)

  # crazy hack because of GAE datastore
  archived = ndb.StringProperty(repeated=True, indexed=True)
  not_archived = ndb.StringProperty(repeated=True, indexed=True)

  recipients = ndb.StringProperty(repeated=True)
