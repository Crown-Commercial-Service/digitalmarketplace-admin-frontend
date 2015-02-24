import requests
import os
from . import main
from flask import json, render_template, Response, request


@main.route('/')
def index():
    return render_template("index.html"), 200


@main.route('/editservice')
def get_service():
    try:
        service_id = request.args.get("service_id")
        service_json = json.loads(get_service_json(service_id))["services"]
        return render_template(
            "edit_service.html", service_data=service_json), 200
    except KeyError:
        return Response("Service ID '%s' can not be found" % service_id, 404)


@main.route('/viewservice')
def get_service_by_id():
    try:
        service_id = request.args.get("service_id")
        service_json = json.loads(get_service_json(service_id))["services"]
        return Response(json.dumps(service_json), mimetype='application/json')
    except KeyError:
        return Response("Service ID '%s' can not be found" % service_id, 404)


def get_service_json(service_id):
    access_token = os.getenv('DM_API_BEARER')
    if access_token is None:
        print('Bearer token must be supplied in DM_API_BEARER')
        raise Exception("DM_API_BEARER token is not set")
    url = \
        "https://api.digitalmarketplace.service.gov.uk/services/" + service_id
    response = requests.get(
        url,
        headers={
            "authorization": "Bearer {}".format(access_token)
        }
    )
    return response.content
