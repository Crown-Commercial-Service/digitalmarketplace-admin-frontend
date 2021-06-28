from datetime import timedelta, datetime

from flask import Flask, request, redirect
from flask_bootstrap import Bootstrap
from flask_login import LoginManager

import dmapiclient
from dmutils import init_app, init_frontend_app, formats
from dmutils.user import User
from dmcontent.content_loader import ContentLoader

from config import configs

import redis
from flask_kvsession import KVSessionExtension
from simplekv.memory.redisstore import RedisStore


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

    if application.config['REDIS_SESSIONS']:
        vcap_services = parse_vcap_services()
        redis_opts = {
            'ssl': application.config['REDIS_SSL'],
            'ssl_ca_certs': application.config['REDIS_SSL_CA_CERTS'],
            'ssl_cert_reqs': application.config['REDIS_SSL_HOST_REQ']
        }
        if vcap_services and 'redis' in vcap_services:
            redis_opts['host'] = vcap_services['redis'][0]['credentials']['hostname']
            redis_opts['port'] = vcap_services['redis'][0]['credentials']['port']
            redis_opts['password'] = vcap_services['redis'][0]['credentials']['password']
        else:
            redis_opts['host'] = application.config['REDIS_SERVER_HOST']
            redis_opts['port'] = application.config['REDIS_SERVER_PORT']
            redis_opts['password'] = application.config['REDIS_SERVER_PASSWORD']

        session_store = RedisStore(redis.StrictRedis(**redis_opts))
        KVSessionExtension(session_store, application)

    application.permanent_session_lifetime = timedelta(hours=12)
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


def parse_vcap_services():
    import os
    import json
    vcap = None
    if 'VCAP_SERVICES' in os.environ:
        try:
            vcap = json.loads(os.environ['VCAP_SERVICES'])
        except ValueError:
            pass
    return vcap
