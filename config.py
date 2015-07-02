import os
import jinja2
from dmutils.status import enabled_since, get_version_label

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DEBUG = True
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_NAME = 'dm_admin_session'
    SESSION_COOKIE_PATH = '/admin'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    S3_DOCUMENT_BUCKET = os.getenv('DM_S3_DOCUMENT_BUCKET')
    DOCUMENTS_URL = 'https://assets.dev.digitalmarketplace.service.gov.uk'
    DM_DATA_API_URL = os.getenv('DM_DATA_API_URL')
    DM_DATA_API_AUTH_TOKEN = os.getenv('DM_DATA_API_AUTH_TOKEN')
    SECRET_KEY = os.getenv('DM_ADMIN_FRONTEND_COOKIE_SECRET')

    STATIC_URL_PATH = '/admin/static'
    ASSET_PATH = STATIC_URL_PATH + '/'
    BASE_TEMPLATE_DATA = {
        'asset_path': ASSET_PATH,
        'header_class': 'with-proposition'
    }

    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_APP_NAME = 'admin-frontend'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        template_folders = [
            os.path.join(repo_root, 'app/templates')
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    AUTHENTICATION = True
    WTF_CSRF_ENABLED = False
    DOCUMENTS_URL = 'https://assets.test.digitalmarketplace.service.gov.uk'
    SECRET_KEY = "test_secret"


class Development(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    AUTHENTICATION = True


class Live(Config):
    DEBUG = False
    AUTHENTICATION = True
    DOCUMENTS_URL = 'https://assets.digitalmarketplace.service.gov.uk'


configs = {
    'development': Development,
    'preview': Live,
    'staging': Live,
    'production': Live,
    'test': Test,
}
