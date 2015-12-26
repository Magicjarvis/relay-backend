# -*- coding: utf-8 -*-
from relay import app

from relay.decorators import jsonify
from relay.models import Relay
from relay.models import SentRelay
from relay.models import delete_db
from relay.util import sanitize_username

@app.route('/test/<user_id>')
@jsonify
def test_latency(user_id):
  return {'Relays': [str(r) for r in Relay.query().iter()],
      'SentRelays': [str(sr) for sr in SentRelay.query().iter()],
      'UserID': sanitize_username(user_id),
      'success': True
  }

@app.route('/clear')
@jsonify
def clear_out_db():
  delete_db()
  return {}
