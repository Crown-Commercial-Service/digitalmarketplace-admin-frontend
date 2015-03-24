import os
from flask import Flask
from flask.ext.bootstrap import Bootstrap
from config import config
from datetime import timedelta
from .main import main as main_blueprint
from .main.helpers.auth import requires_auth

bootstrap = Bootstrap()


def create_app(config_name):

    application = Flask(__name__)
    application.config.from_object(config[config_name])
    config[config_name].init_app(application)

    bootstrap.init_app(application)

    application.register_blueprint(main_blueprint)
    main_blueprint.config = application.config.copy()

    if application.config['AUTHENTICATION']:
        application.permanent_session_lifetime = timedelta(minutes=60)
        application.before_request(requires_auth)

    return application
