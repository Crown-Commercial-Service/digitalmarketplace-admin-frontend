import os
from dmutils.status import enabled_since, get_version_label
from dmutils.asset_fingerprint import AssetFingerprinter

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):

    URL_PREFIX = '/admin'

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DEBUG = True
    SESSION_COOKIE_NAME = 'dm_admin_session'
    SESSION_COOKIE_PATH = '/admin'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True

    CSRF_ENABLED = True
    CSRF_TIME_LIMIT = 8*3600

    DM_MAIN_SERVER_NAME = 'localhost:8000'

    DM_S3_DOCUMENT_BUCKET = None
    DM_DOCUMENTS_URL = 'https://assets.dev.digitalmarketplace.service.gov.uk'
    DM_DATA_API_URL = None
    DM_DATA_API_AUTH_TOKEN = None
    SECRET_KEY = None
    DM_HTTP_PROTO = 'http'
    DM_DEFAULT_CACHE_MAX_AGE = 30
    DM_TIMEZONE = 'Australia/Sydney'

    DM_AGREEMENTS_BUCKET = None
    DM_COMMUNICATIONS_BUCKET = None
    DM_ASSETS_URL = None

    FEATURE_FLAGS = {
    }

    ASSET_PATH = URL_PREFIX + '/static'

    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_APP_NAME = 'admin-frontend'
    DM_LOG_PATH = None
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    SHARED_EMAIL_KEY = None
    INVITE_EMAIL_SALT = 'SupplierInviteEmail'

    GENERIC_CONTACT_EMAIL = 'marketplace@digital.gov.au'
    DM_GENERIC_NOREPLY_EMAIL = 'no-reply@marketplace.digital.gov.au'
    DM_GENERIC_ADMIN_NAME = 'Digital Marketplace Admin'

    INVITE_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    INVITE_EMAIL_FROM = DM_GENERIC_NOREPLY_EMAIL
    INVITE_EMAIL_SUBJECT = 'Your Digital Marketplace invitation'
    CREATE_USER_PATH = 'sellers/create-user'


class Test(Config):
    DEBUG = True
    CSRF_ENABLED = False
    CSRF_FAKED = True
    AUTHENTICATION = True
    DM_DOCUMENTS_URL = 'https://assets.test.digitalmarketplace.service.gov.uk'
    SECRET_KEY = 'TestKeyTestKeyTestKeyTestKeyTestKeyTestKeyX='

    DM_TIMEZONE = 'Australia/Sydney'

    DM_MAIN_SERVER_NAME = 'localhost'

    DM_LOG_LEVEL = 'CRITICAL'
    DM_LOG_PATH = None
    SHARED_EMAIL_KEY = SECRET_KEY
    INVITE_EMAIL_SALT = 'SALT'
    DM_COMMUNICATIONS_BUCKET = 'digitalmarketplace-communications-dev-dev'
    DM_AGREEMENTS_BUCKET = 'digitalmarketplace-documents-dev-dev'


class Development(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    AUTHENTICATION = True
    DM_COMMUNICATIONS_BUCKET = 'digitalmarketplace-communications-dev-dev'
    DM_AGREEMENTS_BUCKET = 'digitalmarketplace-documents-dev-dev'

    DM_DATA_API_URL = "http://localhost:5000"
    DM_DATA_API_AUTH_TOKEN = "myToken"
    SECRET_KEY = 'DevKeyDevKeyDevKeyDevKeyDevKeyDevKeyDevKeyX='
    DM_S3_DOCUMENT_BUCKET = "digitalmarketplace-documents-dev-dev"
    DM_DOCUMENTS_URL = "https://{}.s3-eu-west-1.amazonaws.com".format(DM_S3_DOCUMENT_BUCKET)
    SHARED_EMAIL_KEY = SECRET_KEY
    DM_AGREEMENTS_BUCKET = "digitalmarketplace-agreements-dev-dev"
    DM_COMMUNICATIONS_BUCKET = "digitalmarketplace-communications-dev-dev"


class Live(Config):
    DEBUG = False
    AUTHENTICATION = True
    DM_HTTP_PROTO = 'https'
    DM_DOCUMENTS_URL = 'https://assets.digitalmarketplace.service.gov.uk'
    DM_MAIN_SERVER_NAME = 'marketplace.service.gov.au'


class Staging(Config):
    DEBUG = False
    AUTHENTICATION = True
    DM_DOCUMENTS_URL = 'https://assets.digitalmarketplace.service.gov.uk'


configs = {
    'development': Development,
    'preview': Live,
    'staging': Staging,
    'production': Live,
    'test': Test,
}
