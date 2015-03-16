from pbkdf2 import crypt
import sys
import uuid
import getpass

username = input("Username: ")
password = getpass.getpass()
salt = uuid.uuid4().hex

password_hash = crypt(username + password, salt, iterations=10000)

print(password_hash)
