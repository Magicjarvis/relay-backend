# -*- coding: utf-8 -*-

import logging

from flask import request

from relay import app
from relay.decorators import jsonify

from relay.models.relays import add_relay
from relay.models.users import get_user
from relay.util import extract_url

from gae_python_gcm.gcm import GCMMessage
from gae_python_gcm.gcm import GCMConnection


# util needs to be added somewhere else?
def send_push_notification(sender, recipients, title):
  android_payload = {'sender': sender, 'title': title}
  logging.info('push notification payload %s'%(str(android_payload)))
  #change the way you do this. get the relay object out of that other method.
  # just return metadata, that would be cool
  # TODO
  success = True
  for recipient in recipients.split(','):
    recipient_user = get_user(recipient)

    if recipient_user and len(recipient_user.gcm_ids):
      gcm_message = GCMMessage(recipient_user.gcm_ids, android_payload)
      gcm_conn = GCMConnection()
      logging.info('whaterver this is %s'%(str(gcm_message)))
      gcm_conn.notify_device(gcm_message)
    else:
      success = False
  return success

@app.route('/post_relay_queue', methods=['POST'])
@jsonify
def post_relay():
  url = extract_url(request.form['url'])
  sender = request.form['sender']
  recipients = request.form['recipients']
  if not url:
    return {'success': False}
  relay = add_relay(sender, url, recipients)
  result = relay is not None
  if relay:
    send_push_notification(sender, recipients, relay.title)
  return {'success': result}
