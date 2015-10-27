#!/usr/bin/env python

import os
from app import create_app
from dmutils import init_manager

application = create_app(
    os.getenv('DM_ENVIRONMENT') or 'development'
)
init_manager(application, 5004, ['./app/content/frameworks'])

if __name__ == '__main__':
    manager.run()
