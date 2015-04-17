from flask import Flask
from flask.ext.bootstrap import Bootstrap
from config import config
from datetime import timedelta
from .main import main as main_blueprint
from .status import status as status_blueprint
from .main.helpers.auth import requires_auth

bootstrap = Bootstrap()


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=config[config_name].STATIC_URL_PATH)

    application.config.from_object(config[config_name])
    config[config_name].init_app(application)

    bootstrap.init_app(application)

    if application.config['AUTHENTICATION']:
        application.permanent_session_lifetime = timedelta(minutes=60)
        main_blueprint.before_request(requires_auth)

    application.register_blueprint(status_blueprint)
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    main_blueprint.config = application.config.copy()

    return application
