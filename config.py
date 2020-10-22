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
    SESSION_COOKIE_SAMESITE = 'Lax'

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
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Vcap-Request-Id'

    # Feature Flags
    RAISE_ERROR_ON_MISSING_FEATURES = True

    SHARED_EMAIL_KEY = None
    INVITE_EMAIL_SALT = 'SupplierInviteEmail'
    RESET_PASSWORD_SALT = 'ResetPasswordSalt'
    BUYER_CREATION_TOKEN_SALT = 'BuyerCreation'

    GENERIC_CONTACT_EMAIL = 'marketplace@dta.gov.au'
    DM_GENERIC_NOREPLY_EMAIL = 'no-reply@marketplace.digital.gov.au'
    DM_GENERIC_ADMIN_NAME = 'Digital Marketplace Admin'

    INVITE_EMAIL_NAME = DM_GENERIC_ADMIN_NAME
    INVITE_EMAIL_FROM = DM_GENERIC_NOREPLY_EMAIL
    INVITE_EMAIL_SUBJECT = 'Your Digital Marketplace invitation'
    CREATE_USER_PATH = 'sellers/create-user'
    CREATE_APPLICANT_PATH = 'sellers/signup/create-user'

    REACT_BUNDLE_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/bundle/'
    REACT_RENDER_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/render'
    REACT_RENDER = not DEBUG

    ROLLBAR_TOKEN = None
    S3_BUCKET_NAME = None

    # redis
    REDIS_SESSIONS = True
    REDIS_SERVER_HOST = '127.0.0.1'
    REDIS_SERVER_PORT = 6379
    REDIS_SERVER_PASSWORD = None
    REDIS_SSL = False
    REDIS_SSL_HOST_REQ = None
    REDIS_SSL_CA_CERTS = None


class Test(Config):
    DEBUG = True
    CSRF_ENABLED = False
    CSRF_FAKED = True
    AUTHENTICATION = True
    DM_DOCUMENTS_URL = 'https://assets.test.digitalmarketplace.service.gov.uk'
    SECRET_KEY = 'TestKeyTestKeyTestKeyTestKeyTestKeyTestKeyX='

    DM_TIMEZONE = 'Australia/Sydney'

    DM_MAIN_SERVER_NAME = 'localhost'

    DM_DATA_API_URL = "http://baseurl"
    DM_LOG_LEVEL = 'CRITICAL'
    DM_LOG_PATH = None
    SHARED_EMAIL_KEY = SECRET_KEY
    INVITE_EMAIL_SALT = 'SALT'
    DM_COMMUNICATIONS_BUCKET = 'digitalmarketplace-communications-dev-dev'
    DM_AGREEMENTS_BUCKET = 'digitalmarketplace-documents-dev-dev'

    REACT_BUNDLE_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/bundle/'
    REACT_RENDER_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/render'
    REACT_RENDER = False

    REDIS_SESSIONS = False


class Development(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    AUTHENTICATION = True
    DM_COMMUNICATIONS_BUCKET = 'digitalmarketplace-communications-dev-dev'
    DM_AGREEMENTS_BUCKET = 'digitalmarketplace-documents-dev-dev'

    DM_DATA_API_URL = "http://localhost:5000/api/"
    DM_DATA_API_AUTH_TOKEN = "myToken"
    SECRET_KEY = 'DevKeyDevKeyDevKeyDevKeyDevKeyDevKeyDevKeyX='
    DM_S3_DOCUMENT_BUCKET = "digitalmarketplace-documents-dev-dev"
    DM_DOCUMENTS_URL = "https://{}.s3-eu-west-1.amazonaws.com".format(DM_S3_DOCUMENT_BUCKET)
    SHARED_EMAIL_KEY = SECRET_KEY
    DM_AGREEMENTS_BUCKET = "digitalmarketplace-agreements-dev-dev"
    DM_COMMUNICATIONS_BUCKET = "digitalmarketplace-communications-dev-dev"

    REACT_BUNDLE_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/bundle/'
    REACT_RENDER_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/render'

    REACT_RENDER = True
    DM_SEND_EMAIL_TO_STDERR = True


class Live(Config):
    DEBUG = False
    AUTHENTICATION = True
    DM_HTTP_PROTO = 'https'
    DM_DOCUMENTS_URL = 'https://assets.digitalmarketplace.service.gov.uk'
    DM_MAIN_SERVER_NAME = 'marketplace.service.gov.au'

    REACT_BUNDLE_URL = 'https://dm-frontend.apps.b.cld.gov.au/bundle/'
    REACT_RENDER_URL = 'https://dm-frontend.apps.b.cld.gov.au/render'
    REACT_RENDER = True

    REDIS_SSL = True
    REDIS_SSL_CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'
    REDIS_SSL_HOST_REQ = True


class Staging(Config):
    DEBUG = False
    AUTHENTICATION = True
    DM_DOCUMENTS_URL = 'https://assets.digitalmarketplace.service.gov.uk'
    REACT_BUNDLE_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/bundle/'
    REACT_RENDER_URL = 'https://dm-dev-frontend.apps.y.cld.gov.au/render'
    REACT_RENDER = True
    DM_MAIN_SERVER_NAME = "dm-dev.apps.y.cld.gov.au"

    REDIS_SSL = True
    REDIS_SSL_CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'
    REDIS_SSL_HOST_REQ = True


configs = {
    'development': Development,
    'preview': Live,
    'staging': Staging,
    'production': Live,
    'test': Test,
}
