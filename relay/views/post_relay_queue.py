# -*- coding: utf-8 -*-

import logging

from flask import request

from relay import app
from relay.decorators import jsonify

from relay.models.relays import add_relay
from relay.models.users import get_user
from relay.models.friends import add_friend_request
from relay.util import extract_url

from gae_python_gcm.gcm import GCMMessage
from gae_python_gcm.gcm import GCMConnection


NEW_FRIEND_REQUEST = 'new_friend_request'
NEW_RELAY = 'new_relay'
GCM_CONN = None


def get_gcm_connection():
  global GCM_CONN
  if not GCM_CONN:
    GCM_CONN = GCMConnection()
  return GCM_CONN


def send_new_friend_request_notification(sender, recipient):
  recipient_user = get_user(recipient)
  if recipient_user:
    android_payload = {
      'sender': sender,
      'type': NEW_FRIEND_REQUEST
    }
    send_push_notification(android_payload, recipient_user)


def send_new_relay_notification(sender, recipients, title):
  android_payload = {'sender': sender, 'title': title, 'type': NEW_RELAY}
  for recipient in recipients.split(','):
    recipient_user = get_user(recipient)
    if recipient_user and len(recipient_user.gcm_ids):
      send_push_notification(android_payload, recipient_user)


def send_push_notification(payload, recipient_user):
  payload['user'] = recipient_user.key.id()
  logging.info('Sending %s to %s'%(str(payload), recipient_user))
  if recipient_user and len(recipient_user.gcm_ids):
    gcm_message = GCMMessage(recipient_user.gcm_ids, payload)
    get_gcm_connection().notify_device(gcm_message)


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
    send_new_relay_notification(sender, recipients, relay.title)
  return {'success': result}


@app.route('/post_friend_request_queue', methods=['POST'])
@jsonify
def post_friend_request_to_queue():
  sender = request.form['sender']
  recipient = request.form['recipient']
  if not sender or not recipient:
    return {'success': False}
  friend_request = add_friend_request(sender, recipient)
  result = friend_request is not None
  if friend_request:
    send_new_friend_request_notification(sender, recipient)
  return {'success': result}
