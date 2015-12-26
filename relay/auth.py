# -*- coding: utf-8 -*-
import base64

from Crypto import Random
from passlib.hash import sha256_crypt

def generate_session_id():
  return base64.b64encode(Random.get_random_bytes(16))

def hash_password(password):
  return sha256_crypt.encrypt(password)

def verify_password(attempt, hashed_password):
  return sha256_crypt.verify(attempt, hashed_password)
