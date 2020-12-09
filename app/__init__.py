from copy import deepcopy
from datetime import timedelta

from dmcontent.errors import ContentNotFoundError
from flask import Flask, request, redirect, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.local import Local, LocalProxy

import dmapiclient
from dmcontent.content_loader import ContentLoader
from dmutils import init_app, formats
from dmutils.timing import logged_duration
from dmutils.user import User
from govuk_frontend_jinja.flask_ext import init_govuk_frontend

from config import configs


csrf = CSRFProtect()
data_api_client = dmapiclient.DataAPIClient()
login_manager = LoginManager()

# we use our own Local for objects we explicitly want to be able to retain between requests but shouldn't
# share a common object between concurrent threads/contexts
_local = Local()

# These frameworks pre-date the introduction of the edit_service_as_admin and declaration manifests.
OLD_FRAMEWORKS_WITH_MISSING_MANIFESTS = ['g-cloud-4', 'g-cloud-5', 'g-cloud-6']


def _log_missing_manifest(application, manifest_name, framework_slug):
    if framework_slug in OLD_FRAMEWORKS_WITH_MISSING_MANIFESTS:
        logger = application.logger.debug
    else:
        logger = application.logger.error

    logger(
        f"Could not load {manifest_name} manifest for {framework_slug}"
    )


def _make_content_loader_factory(application, frameworks, initial_instance=None):
    # for testing purposes we allow an initial_instance to be provided
    master_cl = initial_instance if initial_instance is not None else ContentLoader('app/content')
    for framework_data in frameworks:
        try:
            master_cl.load_manifest(framework_data['slug'], 'services', 'edit_service_as_admin')
        except ContentNotFoundError:
            _log_missing_manifest(application, "edit_service_as_admin", framework_data['slug'])
        try:
            master_cl.load_manifest(framework_data['slug'], 'declaration', 'declaration')
        except ContentNotFoundError:
            _log_missing_manifest(application, "declaration", framework_data['slug'])

    # seal master_cl in a closure by returning a function which will only ever return an independent copy of it.
    # this is of course only guaranteed when the initial_instance argument wasn't used.
    return lambda: deepcopy(master_cl)


def _content_loader_factory():
    # this is a placeholder _content_loader_factory implementation that should never get called, instead being
    # replaced by one created using _make_content_loader_factory once an `application` is available to
    # initialize it with
    raise LookupError("content loader not ready yet: must be initialized & populated by create_app")


@logged_duration(message="Spent {duration_real}s in get_content_loader")
def get_content_loader():
    if not hasattr(_local, "content_loader"):
        _local.content_loader = _content_loader_factory()
    return _local.content_loader


content_loader = LocalProxy(get_content_loader)
from app.main.helpers.service import parse_document_upload_time


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    # allow using govuk-frontend Nunjucks templates
    init_govuk_frontend(application)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        login_manager=login_manager,
    )

    # replace placeholder _content_loader_factory with properly initialized one
    global _content_loader_factory
    _content_loader_factory = _make_content_loader_factory(
        application,
        data_api_client.find_frameworks().get('frameworks'),
    )

    from .metrics import metrics as metrics_blueprint, gds_metrics
    from .main import main as main_blueprint
    from .main import public as public_blueprint
    from .status import status as status_blueprint
    from dmutils.external import external as external_blueprint

    application.register_blueprint(metrics_blueprint, url_prefix='/admin')
    application.register_blueprint(status_blueprint, url_prefix='/admin')
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    application.register_blueprint(public_blueprint, url_prefix='/admin')

    # Must be registered last so that any routes declared in the app are registered first (i.e. take precedence over
    # the external NotImplemented routes in the dm-utils external blueprint).
    application.register_blueprint(external_blueprint)

    login_manager.login_message = None  # don't flash message to user
    login_manager.login_view = '/user/login'
    main_blueprint.config = application.config.copy()

    # Should be incorporated into digitalmarketplace-utils as well
    gds_metrics.init_app(application)
    csrf.init_app(application)

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    application.add_template_filter(parse_document_upload_time)

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
