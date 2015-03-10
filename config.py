import os
import jinja2

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = True
    S3_DOCUMENT_BUCKET = os.getenv('DM_S3_DOCUMENT_BUCKET')
    API_URL = os.getenv('DM_API_URL'),
    API_AUTH_TOKEN = os.getenv('DM_ADMIN_FRONTEND_API_AUTH_TOKEN')
    BASE_TEMPLATE_DATA = {}

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        template_folders = [
            os.path.join(repo_root,
                         'bower_components/govuk_template/views/layouts'),
            os.path.join(repo_root, 'app/templates')
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    AUTHENTICATION = False
    BASE_TEMPLATE_DATA = {
        'asset_path': '/static/',
        'header_class': 'with-proposition'
    }


class Development(Config):
    DEBUG = True
    AUTHENTICATION = True
    BASE_TEMPLATE_DATA = {
        'asset_path': '/static/',
        'header_class': 'with-proposition'
    }


class Live(Config):
    DEBUG = False
    AUTHENTICATION = True
    BASE_TEMPLATE_DATA = {
        'asset_path': '/static/',
        'header_class': 'with-proposition'
    }


config = {
    'live': Live,
    'development': Development,
    'test': Test,
    'default': Development
}
