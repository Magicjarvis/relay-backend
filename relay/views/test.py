# -*- coding: utf-8 -*-
from relay import app

from relay.decorators import jsonify
from relay.decorators import session_required
from relay.models.relays import Relay
from relay.models.relays import SentRelay
from relay.models import delete_db
from relay.util import sanitize_username

from flask import request

@app.route('/test/<user_id>')
@jsonify
@session_required
def test_latency(user_id, user=None):
  return {'Relays': [str(r) for r in Relay.query().iter()],
      'SentRelays': [str(sr) for sr in SentRelay.query().iter()],
      'UserID': sanitize_username(user_id),
      'success': True,
      'authorization': request.headers.get('Authorization', 'None Specified'),
      'user': str(user)
  }

@app.route('/clear')
@jsonify
def clear_out_db():
  drop_users = bool(request.args.get('drop_users', 0))
  delete_db(drop_users=drop_users)
  return {}
