# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
from metadata import scrape as scrape_metadata
from util import sanitize_username
import tldextract

def get_relays(sent_relay_id, offset):
  if sent_relay_id is not None:
    return str(SentRelay.get_by_id(sent_relay_id))

  sent_relays = []
  for sent_relay in SentRelay.query().iter():
    relay = sent_relay.relay.get()
    relay_index = RelayIndex.query(ancestor=sent_relay.key).get()
    item = {
        'id':sent_relay.key.id(),
        'sender': sent_relay.sender,
        'recipients': sent_relay.to,
        'title': relay.title,
        'description': relay.description,
        'image': relay.image,
        'favicon': relay.favicon,
        'site': relay.site,
        'url': relay.key.id(),
        'kind': relay.kind
    }
    sent_relays.append(item)
  return sent_relays

@ndb.transactional(xg=True)
def add_friend(user, other_user):
  Friendship(user=user, other_user=other_user).put()
  Friendship(user=other_user, other_user=user).put()
  return True

def strip_tags(url):
  extracted = tldextract.extract(url)
  subdomains = filter(lambda x: x != 'www', extracted.subdomain.split('.'))
  return subdomains + [extracted.domain]

@ndb.transactional(xg=True)
def add_relay(sender, url, recipients):
  #TODO: break this shit up

  relay = Relay.get_by_id(url)
  if recipients:
    recipients = map(sanitize_username, recipients.split(','))
  else:
    recipients = []

  # sender can't be in recipient list. it's 4:25am and i'm tired of that crap
  if sender in recipients:
    recipients.remove(sender)

  if relay is None:
    metadata = scrape_metadata(url)
    relay = Relay(**metadata)
    relay.title = relay.title or url
    if (relay.description is not None):
      relay.description = relay.description.strip()

  relay_key = relay.put()

  sent_relay = SentRelay()
  sent_relay.sender = sanitize_username(sender)
  sent_relay.relay = relay_key
  sent_relay.to = recipients # this is a copy that isn't modify

  sent_relay_key = sent_relay.put()

  # If all the user did was save
  if len(recipients) == 0:
    return relay

  ri = RelayIndex(parent=sent_relay.key)
  ri.recipients = recipients
  ri_key = ri.put()
  tag_model = RelayTags(parent=sent_relay.key)
  tag_model.tags = [relay.site] if relay.site else []
  tag_key = tag_model.put()
  #error if things don't work
  return relay

def delete_db():
  ndb.delete_multi(User.query().fetch(keys_only=True))
  ndb.delete_multi(RelayTags.query().fetch(keys_only=True))
  ndb.delete_multi(Relay.query().fetch(keys_only=True))
  ndb.delete_multi(RelayIndex.query().fetch(keys_only=True))
  ndb.delete_multi(SentRelay.query().fetch(keys_only=True))
  ndb.delete_multi(Friendship.query().fetch(keys_only=True))
  ndb.delete_multi(FriendRequest.query().fetch(keys_only=True))

class User(ndb.Model):
  """Models a user."""
  password = ndb.StringProperty(required=True)
  email = ndb.StringProperty()

  session_token = ndb.StringProperty(indexed=True) # probably wanna index this?
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
  # The id is the url. There shouldn't be a way to create a Relay without a
  # url id
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

  # who the relay was sent to. should be a copy of recipients in RelayIndex,
  # but shouldn't be mutated
  to = ndb.StringProperty(repeated=True)

  # a saved relay is defined as being sent to no one
  saved = ndb.ComputedProperty(lambda self: len(self.to) == 0)

class RelayTags(ndb.Model):
  # create a thing for this so that i can look at all of the tags
  # and perform a smart query about it
  """Models the recipients of the url. Split for performance."""
  tags = ndb.StringProperty(repeated=True)

class RelayIndex(ndb.Model):
  """Models the recipients of the url. Split for performance."""
  # duplicate because i couldn't figure out how to query it. need to sort by
  # this
  timestamp = ndb.DateTimeProperty(indexed=True, auto_now_add=True)
  recipients = ndb.StringProperty(repeated=True)
