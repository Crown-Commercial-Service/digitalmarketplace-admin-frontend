#!/usr/bin/env python

import os
from app import create_app
from flask.ext.script import Manager, Server
from dmutils import init_manager

application = create_app(
    os.getenv('DM_ENVIRONMENT') or 'development'
)
manager = Manager(application)
init_manager(manager, 5004, ['./app/content/frameworks'])

if __name__ == '__main__':
    manager.run()
