from datetime import timedelta, datetime

from flask import Flask, request, redirect
from flask.ext.bootstrap import Bootstrap
from flask_login import LoginManager
from flask_wtf.csrf import CsrfProtect

import dmapiclient
from dmutils import init_app, flask_featureflags, formats
from dmutils.user import User
from dmcontent.content_loader import ContentLoader

from config import configs


bootstrap = Bootstrap()
csrf = CsrfProtect()
data_api_client = dmapiclient.DataAPIClient()
feature_flags = flask_featureflags.FeatureFlag()
login_manager = LoginManager()

content_loader = ContentLoader('app/content')
content_loader.load_manifest('g-cloud-6', 'services', 'edit_service_as_admin')
content_loader.load_manifest('g-cloud-7', 'declaration', 'declaration')
content_loader.load_manifest('digital-outcomes-and-specialists', 'declaration', 'declaration')

from app.main.helpers.service import parse_document_upload_time


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    init_app(
        application,
        configs[config_name],
        bootstrap=bootstrap,
        data_api_client=data_api_client,
        feature_flags=feature_flags,
        login_manager=login_manager
    )
    # Should be incorporated into digitalmarketplace-utils as well
    csrf.init_app(application)

    application.permanent_session_lifetime = timedelta(hours=1)
    from .main import main as main_blueprint
    from .status import status as status_blueprint

    application.register_blueprint(status_blueprint, url_prefix='/admin')
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    login_manager.login_view = 'main.render_login'
    main_blueprint.config = application.config.copy()

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            return redirect(request.path[:-1], code=301)

    application.add_template_filter(parse_document_upload_time)

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
