from datetime import timedelta, datetime

from flask import Flask, request, redirect
from flask.ext.bootstrap import Bootstrap
from flask_login import LoginManager
from flask_wtf.csrf import CsrfProtect
from dmutils import apiclient, init_app, flask_featureflags, formats
from dmutils.user import User
from dmutils.content_loader import ContentLoader

from config import configs


bootstrap = Bootstrap()
csrf = CsrfProtect()
data_api_client = apiclient.DataAPIClient()
feature_flags = flask_featureflags.FeatureFlag()
login_manager = LoginManager()
DISPLAY_DATE_FORMAT = '%d/%m/%Y'
DISPLAY_TIME_FORMAT = '%H:%M:%S'
DISPLAY_DATETIME_FORMAT = '%A, %d %B %Y at %H:%M'

service_content = ContentLoader(
    "app/section_order.yml", "app/content/g6/"
)


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

    @application.template_filter('timeformat')
    def timeformat(value):
        return datetime.strptime(
            value, formats.DATETIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)

    @application.template_filter('dateformat')
    def dateformat(value):
        return datetime.strptime(
            value, formats.DATETIME_FORMAT).strftime(DISPLAY_DATE_FORMAT)

    @application.template_filter('displaydateformat')
    def display_date_format(value):
        return value.strftime(DISPLAY_DATE_FORMAT)

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(user_id)
