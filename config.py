import os
import jinja2
from dmutils.status import get_version_label
from dmutils.asset_fingerprint import AssetFingerprinter

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):

    VERSION = get_version_label(
        os.path.abspath(os.path.dirname(__file__))
    )
    DEBUG = True
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_NAME = 'dm_session'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True

    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    DM_COOKIE_PROBE_EXPECT_PRESENT = True

    DM_S3_DOCUMENT_BUCKET = None
    DM_DATA_API_URL = None
    DM_DATA_API_AUTH_TOKEN = None
    SECRET_KEY = None

    DM_AGREEMENTS_BUCKET = None
    DM_COMMUNICATIONS_BUCKET = None
    DM_REPORTS_BUCKET = None
    DM_ASSETS_URL = None

    STATIC_URL_PATH = '/admin/static'
    ASSET_PATH = STATIC_URL_PATH + '/'
    BASE_TEMPLATE_DATA = {
        'header_class': 'with-proposition',
        'asset_path': ASSET_PATH,
        'asset_fingerprinter': AssetFingerprinter(asset_root=ASSET_PATH)
    }

    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_PLAIN_TEXT_LOGS = False
    DM_APP_NAME = 'admin-frontend'

    SHARED_EMAIL_KEY = None
    INVITE_EMAIL_SALT = 'InviteEmailSalt'

    DM_NOTIFY_API_KEY = None

    NOTIFY_TEMPLATES = {
        "invite_contributor": "5eefe42d-1694-4388-8908-991cdfba0a71",
    }

    # a mapping of framework slug to identifier on performance platform containing signup stats
    PERFORMANCE_PLATFORM_ID_MAPPING = {
        "g-cloud-9": "g-cloud-9-supplier-applications",
        "g-cloud-10": "g-cloud-10-supplier-applications",
        "g-cloud-11": "g-cloud-11-supplier-applications",
        "digital-outcomes-and-specialists-3": "digital-outcomes-specialists-3",
        "digital-outcomes-and-specialists-4": "digital-outcomes-specialists-4",
    }
    PERFORMANCE_PLATFORM_BASE_URL = "https://www.gov.uk/performance/"

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        digitalmarketplace_govuk_frontend = os.path.join(repo_root, "node_modules", "digitalmarketplace-govuk-frontend")

        template_folders = [
            os.path.join(repo_root, "app", "templates"),
            os.path.join(digitalmarketplace_govuk_frontend),
            os.path.join(digitalmarketplace_govuk_frontend, "digitalmarketplace", "templates"),
            os.path.join(digitalmarketplace_govuk_frontend, "govuk-frontend"),
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True
    AUTHENTICATION = True
    WTF_CSRF_ENABLED = False
    DM_ASSETS_URL = 'https://assets.test.digitalmarketplace.service.gov.uk'
    SECRET_KEY = "test_secret"

    DM_LOG_LEVEL = 'CRITICAL'
    SHARED_EMAIL_KEY = 'KEY'
    INVITE_EMAIL_SALT = 'SALT'
    DM_NOTIFY_API_KEY = "not_a_real_key-00000000-fake-uuid-0000-000000000000"


class Development(Config):
    DEBUG = True
    DM_PLAIN_TEXT_LOGS = True
    SESSION_COOKIE_SECURE = False
    AUTHENTICATION = True
    DM_AGREEMENTS_BUCKET = 'digitalmarketplace-dev-uploads'
    DM_COMMUNICATIONS_BUCKET = 'digitalmarketplace-dev-uploads'
    DM_S3_DOCUMENT_BUCKET = "digitalmarketplace-dev-uploads"
    DM_REPORTS_BUCKET = "digitalmarketplace-dev-uploads"
    DM_ASSETS_URL = "https://{}.s3-eu-west-1.amazonaws.com".format(DM_S3_DOCUMENT_BUCKET)

    DM_DATA_API_URL = f"http://localhost:{os.getenv('DM_API_PORT', 5000)}"
    DM_DATA_API_AUTH_TOKEN = "myToken"
    SECRET_KEY = "verySecretKey"
    DM_NOTIFY_API_KEY = "not_a_real_key-00000000-fake-uuid-0000-000000000000"
    SHARED_EMAIL_KEY = "very_secret"


class Live(Config):
    DEBUG = False
    AUTHENTICATION = True
    DM_HTTP_PROTO = 'https'

    # use of invalid email addresses with live api keys annoys Notify
    DM_NOTIFY_REDIRECT_DOMAINS_TO_ADDRESS = {
        "example.com": "success@simulator.amazonses.com",
        "example.gov.uk": "success@simulator.amazonses.com",
        "user.marketplace.team": "success@simulator.amazonses.com",
    }


configs = {
    'development': Development,
    'preview': Live,
    'staging': Live,
    'production': Live,
    'test': Test,
}
