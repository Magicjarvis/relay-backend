# -*- coding: utf-8 -*-
import logging 

from flask import request

from relay import app
from relay.decorators import jsonify
from relay.decorators import session_required
from relay.decorators import sanitize_user

from relay.models.relays import add_relay_model
from relay.models.relays import get_relay
from relay.models.relays import get_relays
from relay.models.relays import get_relays_for_recipient
from relay.models.relays import get_sent_relay
from relay.models.relays import get_sent_relays_for_user

from relay.util import extract_url
from relay.util import make_relay_map
from relay.util import make_sent_relay_map

# remove the direct models from these files, but babysteps
from google.appengine.api import taskqueue


@app.route('/relays/preview')
@jsonify
def relay_preview():
  # standardize the url so that we maximize our caching
  url = extract_url(request.args.get('url'))
  if not url:
    return {}
  relay = get_relay(url)
  if not relay:
    relay = add_relay_model(url)
    relay.put()
  return make_relay_map(relay)


@app.route('/relays/<user_id>/archive', methods=['POST'])
@jsonify
@sanitize_user
@session_required
def archive_relay(user_id, user=None):
  sent_relay_id = long(request.form['relay_id'])
  sent_relay = get_sent_relay(sent_relay_id)
  sent_relay.not_archived.remove(user_id)
  sent_relay.archived.append(user_id)
  result = sent_relay.put()
  logging.info('archiving sent_relay %s'%(str(sent_relay)))
  return {'success': result is not None}


@app.route('/relays', methods=['GET', 'POST'])
@app.route('/relays/<int:sent_relay_id>')
@jsonify
def reelay(sent_relay_id=None):
  if request.method == 'GET':
    offset = int(request.args.get('offset', 0))
    return {'relays': get_relays(sent_relay_id, offset)}
  elif request.method == 'POST':
    task = queue_relay(
      request.form['url'],
      request.form['sender'],
      request.form['recipients'],
    )
    return {'success': task.was_enqueued}

def queue_relay(url, sender, recipients):
  task = taskqueue.add(
    url='/post_relay_queue',
    params={
      'url': url,
      'sender': sender,
      'recipients': recipients,
    }
  )
  return task.was_enqueued


@app.route('/relays/<user_id>/delete', methods=['POST'])
@jsonify
@sanitize_user
@session_required
def delete_relay(user_id, user=None):
  sent_relay_id = long(request.form['relay_id'])
  sent_relay = get_sent_relay(sent_relay_id)
  recipients = sent_relay.recipients
  success = False

  # validate this
  if user_id == sent_relay.sender:
    sent_relay.key.delete()
    success = True

  if user_id in recipients:
    recipients.remove(user_id)
    sent_relay.put()
    success = True

  return {'success': success}


@app.route('/relays/from/<user_id>')
@jsonify
@sanitize_user
@session_required
def get_relays_from_user(user_id=None, user=None):
  offset = int(request.args.get('offset', 0))
  limit = int(request.args.get('limit', 10))

  sent_relays = []

  sent_relay_items = get_sent_relays_for_user(user_id, offset=offset, limit=limit)
  for sent_relay_item in sent_relay_items:
    item_map = make_sent_relay_map(sent_relay_item)
    item_map.pop('sender', None)
    if user_id in sent_relay_item.recipients:
      continue
    item_map['recipients'] = sent_relay_item.recipients
    sent_relays.append(item_map)
  return {'relays': sent_relays}
  

@app.route('/relays/to/<user_id>')
@jsonify
@sanitize_user
@session_required
def get_relay_to_user(user_id=None, user=None, archived=False):
  archived = bool(int(request.args.get('archived', 0)))
  return _get_relay_to_user(user_id, user, archived)

def _get_relay_to_user(user_id=None, user=None, archived=False):
  offset = int(request.args.get('offset', 0))
  relays = get_relays_for_recipient(user_id, offset, archived=archived)
  return {
    'relays' : [
      make_sent_relay_map(r) for r in relays
    ]
  }
