# -*- coding: utf-8 -*-
import logging
from relay.metadata import scrape as scrape_metadata
from relay.util import sanitize_username
from google.appengine.ext import ndb


def get_relay(relay_id):
  return Relay.get_by_id(relay_id)


def get_sent_relay(sent_relay_id):
  return SentRelay.get_by_id(sent_relay_id)


def get_sent_relays_for_user(user, limit=10, offset=0):
  return SentRelay.query().order(
    -SentRelay.timestamp
  ).filter(
    SentRelay.sender == user
  ).iter(options=ndb.QueryOptions(limit=limit, offset=offset))

def get_relays_for_recipient(user_id, offset, archived=False):
  qo = ndb.QueryOptions(limit=10, offset=offset)
  archive_clause = SentRelay.archived if archived else SentRelay.not_archived
  sent_relays_iter = SentRelay.query().filter(
    archive_clause == user_id,
  ).order(
    -SentRelay.timestamp
  ).iter(options=qo)
  sent_relays = [item for item in sent_relays_iter]
  logging.info('get_relay_for_recipient(%s) -> %s'%(user_id, str(sent_relays)))
  return sent_relays


def get_relays(sent_relay_id, offset):
  """Dumb test method for /relays which isn't used by clients"""
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

  if relay is None:
    relay = add_relay_model(url)

  relay_key = relay.put()
  if not recipients:
    # we go ahead and make a relay for caching purposes
    # dont go further than that
    return None

  sent_relay = SentRelay()
  sent_relay.sender = sanitize_username(sender)
  sent_relay.relay = relay_key
  sent_relay.recipients = recipients # canonical list of recipients
  sent_relay.not_archived = recipients # dirty hack for no != on indexes
  sent_relay.saved = save

  sent_relay_key = sent_relay.put()

  # this should be a sent_relay but whatever
  return relay

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

  # crazy hack because of GAE datastore
  archived = ndb.StringProperty(repeated=True, indexed=True)
  not_archived = ndb.StringProperty(repeated=True, indexed=True)

  recipients = ndb.StringProperty(repeated=True)
