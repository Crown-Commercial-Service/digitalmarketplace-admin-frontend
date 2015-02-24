from flask import Flask
from flask.ext.bootstrap import Bootstrap


bootstrap = Bootstrap()


def create_app(config_name):

    application = Flask(__name__)
    application.config['DEBUG'] = True

    bootstrap.init_app(application)

    from .main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    return application
