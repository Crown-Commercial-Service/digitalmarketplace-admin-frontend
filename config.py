import os
import jinja2

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
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


class Development(Config):
    DEBUG = True


class Live(Config):
    DEBUG = False


config = {
    'live': Live,
    'development': Development,
    'test': Test,
    'default': Development
    }
