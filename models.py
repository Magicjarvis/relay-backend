from google.appengine.ext import ndb
from metadata import scrape as scrape_metadata
import tldextract

def get_relays(sent_relay_id):
  if sent_relay_id is not None:
    return str(SentRelay.get_by_id(sent_relay_id))

  sent_relays = []
  for sent_relay in SentRelay.query().iter():
    relay = sent_relay.relay.get()
    relay_index = RelayIndex.query(ancestor=sent_relay.key).get()
    recipients = relay_index.recipients if relay_index is not None else []
    item = {
        'id':sent_relay.key.id(),
        'sender': sent_relay.sender,
        'recipients': recipients,
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

def add_friend(sender_name, recipient_name):
  recipient = User.get_by_id(recipient_name)
  sender = User.get_by_id(sender_name)
  if None in [sender, recipient]:
    return False
  sender_index = UserIndex.get_or_insert(sender_name, parent=sender.key)
  sender_friends = sender_index.friends
  if recipient_name not in sender_friends:
    sender_friends.append(recipient_name)
    sender_index.put()

  return True

def strip_tags(url):
  extracted = tldextract.extract(url)
  subdomains = filter(lambda x: x != 'www', extracted.subdomain.split('.'))
  return subdomains + [extracted.domain]

@ndb.transactional(xg=True)
def add_relay(sender, url, recipients):
  #TODO: break this shit up

  relay = Relay.get_by_id(url)

  if relay is None:
    metadata = scrape_metadata(url)
    relay = Relay(**metadata)
    relay.title = relay.title or url
    if (relay.description is not None):
      relay.description = relay.description.strip()

  relay_key = relay.put()

  sent_relay = SentRelay()
  sent_relay.sender = sender
  sent_relay.relay = relay_key

  sent_relay_key = sent_relay.put()

  ri = RelayIndex(parent=sent_relay.key)
  ri.recipients = recipients.split(',')
  ri_key = ri.put()
  tag_model = RelayTags(parent=sent_relay.key)
  tag_model.tags = [metadata['site']] if metadata['site'] else []
  tag_key = tag_model.put()
  return all([sent_relay_key, ri_key, tag_key])

class User(ndb.Model):
  """Models a user."""
  display_name = ndb.StringProperty()
  password = ndb.StringProperty(required=True)

class UserIndex(ndb.Model):
  """Adds the friendship aspect to the user model."""
  friends = ndb.StringProperty(repeated=True)

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
  stale = ndb.BooleanProperty(default=False)

class RelayTags(ndb.Model):
  # create a thing for this so that i can look at all of the tags
  # and perform a smart query about it
  """Models the recipients of the url. Split for performance."""
  tags = ndb.StringProperty(repeated=True)

class RelayIndex(ndb.Model):
  """Models the recipients of the url. Split for performance."""
  recipients = ndb.StringProperty(repeated=True)
