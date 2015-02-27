import requests
import os
import re
from flask import json, render_template, Response, request, redirect
from . import main, content_configuration


@main.route('/')
def index():
    template_data = main.config['BASE_TEMPLATE_DATA']
    return render_template("index.html", **template_data)


@main.route('/service')
def find_service():
    service_id = request.args.get("service_id")
    return redirect("/service/" + service_id)


@main.route('/service/<service_id>')
def view_service(service_id):
    template_data = main.config['BASE_TEMPLATE_DATA']
    template_data['sections'] = content_configuration.get_sections()
    try:
        template_data["service_data"] = json.loads(
            get_service_json(service_id)
        )["services"]
        template_data["service_data"]["id_split"] = re.findall(
            "....", str(template_data["service_data"]["id"])
        )
        return render_template("view_service.html", **template_data)
    except KeyError:
        return Response("Service ID '%s' can not be found" % service_id, 404)


@main.route('/service/<service_id>/edit/<section>')
def edit_section(service_id, section):
    template_data = main.config['BASE_TEMPLATE_DATA']
    template_data['section'] = content_configuration.get_section(section)
    try:
        template_data["service_data"] = json.loads(
            get_service_json(service_id)
        )["services"]
        return render_template("edit_section.html", **template_data)
    except KeyError:
        return Response("Service ID '%s' can not be found" % service_id, 404)


@main.route('/service/<service_id>', methods=['POST'])
def update(service_id):
    template_data = main.config['BASE_TEMPLATE_DATA']
    template_data["edits_submitted"] = request.form
    template_data["service_id"] = service_id
    return render_template("confirm.html", **template_data), 200


def get_service_json(service_id):
    # TODO: Don't do these checks for every call - initialise once
    access_token = os.getenv('DM_API_BEARER')
    api_url = os.getenv('DM_API_URL')
    if access_token is None:
        print('Bearer token must be supplied in DM_API_BEARER')
        raise Exception("DM_API_BEARER token is not set")
    if api_url is None:
        print('API URL must be supplied in DM_API_URL')
        raise Exception("DM_API_URL is not set")
    url = api_url + "/services/" + service_id
    response = requests.get(
        url,
        headers={
            "authorization": "Bearer {}".format(access_token)
        }
    )
    return response.content
