# -*- coding: utf-8 -*-
"""setup flask app and initialize views .. the import strategy here isn't
good, but it's a start for splitting up files.
"""
from flask import Flask, request
app = Flask(__name__.split('.')[0])

import views.users
import views.relays
import views.login
import views.post_relay_queue
import views.friend_requests
import views.test
