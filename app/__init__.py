from datetime import timedelta, datetime

from flask import Flask, request, redirect
from flask_bootstrap import Bootstrap
from flask_login import LoginManager

import dmapiclient
from dmutils import init_app, init_frontend_app, formats
from dmutils.user import User
from dmcontent.content_loader import ContentLoader

from config import configs


bootstrap = Bootstrap()
data_api_client = dmapiclient.DataAPIClient()
login_manager = LoginManager()

content_loader = ContentLoader('app/content')
content_loader.load_manifest('g-cloud-6', 'services', 'edit_service_as_admin')
content_loader.load_manifest('g-cloud-7', 'declaration', 'declaration')
content_loader.load_manifest('digital-outcomes-and-specialists', 'declaration', 'declaration')
content_loader.load_manifest('g-cloud-8', 'declaration', 'declaration')

from app.main.helpers.service import parse_document_upload_time  # noqa


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].ASSET_PATH)

    init_app(
        application,
        configs[config_name],
        bootstrap=bootstrap,
        data_api_client=data_api_client,
        login_manager=login_manager
    )

    application.permanent_session_lifetime = timedelta(hours=1)
    from .main import main as main_blueprint
    from .status import status as status_blueprint

    url_prefix = application.config['URL_PREFIX']
    application.register_blueprint(status_blueprint, url_prefix=url_prefix)
    application.register_blueprint(main_blueprint, url_prefix=url_prefix)
    login_manager.login_view = 'main.render_login'
    main_blueprint.config = application.config.copy()

    init_frontend_app(application, data_api_client, login_manager)

    application.add_template_filter(parse_document_upload_time)

    @application.context_processor
    def extra_template_variables():
        return {
            'generic_contact_email': application.config['GENERIC_CONTACT_EMAIL'],
        }

    return application
