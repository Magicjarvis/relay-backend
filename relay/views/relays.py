# -*- coding: utf-8 -*-
import logging 

from flask import request

from relay import app
from relay.decorators import jsonify
from relay.decorators import validate_user

from relay.models import Relay
from relay.models import SentRelay
from relay.models import add_relay_model
from relay.models import get_relays
from relay.models import get_relays_for_recipient

from relay.util import make_relay_map
from relay.util import make_sent_relay_map

# remove the direct models from these files, but babysteps
from google.appengine.ext import ndb
from google.appengine.api import taskqueue


@app.route('/relays/preview')
@jsonify
def relay_preview():
  url = request.args.get('url')
  if not url:
    return {}
  relay = Relay.get_by_id(url)
  if not relay:
    relay = add_relay_model(url)
    relay.put()
  return make_relay_map(relay)


@app.route('/relays/<user_id>/archive', methods=['POST'])
@jsonify
def archive_relay(user_id):
  sent_relay_id = long(request.form['relay_id'])
  sent_relay = SentRelay.get_by_id(sent_relay_id)
  sent_relay.not_archived.remove(user_id)
  sent_relay.archived.append(user_id)
  result = sent_relay.put()
  logging.info('sent_relay %s'%(str(sent_relay)))
  return {'success': result is not None}


@app.route('/relays', methods=['GET', 'POST'])
@app.route('/relays/<int:sent_relay_id>')
@jsonify
def reelay(sent_relay_id=None):
  if request.method == 'GET':
    offset = int(request.args.get('offset', 0))
    return {'relays': get_relays(sent_relay_id, offset)}
  elif request.method == 'POST':
    task = taskqueue.add(
      url='/post_relay_queue',
      params={
        'url': request.form['url'],
        'sender': request.form['sender'],
        'recipients': request.form['recipients'],
      }
    )
    return {'success': task.was_enqueued}


@app.route('/relays/<user_id>/delete', methods=['POST'])
@jsonify
def delete_relay(user_id):
  relay_id = long(request.form['relay_id'])
  sent_relay = SentRelay.get_by_id(relay_id) 
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
@validate_user
def get_relays_from_user(user_id=None):
  offset = int(request.args.get('offset', 0))
  qo = ndb.QueryOptions(limit=10, offset=offset)
  sent_relay_items = SentRelay.query().order(-SentRelay.timestamp).filter(SentRelay.sender == user_id).filter(SentRelay.saved == False).iter(options=qo)
  sent_relays = []
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
@validate_user
def get_relay_to_user(user_id=None):
  offset = int(request.args.get('offset', 0))
  relays = get_relays_for_recipient(user_id, offset)
  return {
    'relays' : [
      make_sent_relay_map(r) for r in relays
      if r.sender != user_id
    ]
  }
