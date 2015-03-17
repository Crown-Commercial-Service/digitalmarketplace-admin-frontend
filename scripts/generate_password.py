#!/usr/bin/env python
# encoding: utf-8

from pbkdf2 import crypt
import uuid
import getpass
import base64

username = raw_input("Username: ")
password = getpass.getpass()
salt = uuid.uuid4().hex

password_hash = base64.b64encode(
    crypt(username + password, salt, iterations=10000)
)

print(password_hash)
