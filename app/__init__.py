from datetime import timedelta

from flask import Flask
from flask.ext.bootstrap import Bootstrap
from dmutils import apiclient, config, logging

from config import configs


bootstrap = Bootstrap()
data_api_client = apiclient.DataAPIClient()


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    application.config.from_object(configs[config_name])
    configs[config_name].init_app(application)
    config.init_app(application)

    bootstrap.init_app(application)
    logging.init_app(application)
    data_api_client.init_app(application)

    from .main import main as main_blueprint
    from .status import status as status_blueprint

    if application.config['AUTHENTICATION']:
        from .main.helpers.auth import requires_auth
        application.permanent_session_lifetime = timedelta(minutes=60)
        main_blueprint.before_request(requires_auth)

    application.register_blueprint(status_blueprint)
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    main_blueprint.config = application.config.copy()

    return application
