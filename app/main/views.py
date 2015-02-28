import requests
import os
import re
from flask import json, render_template, Response, request, redirect, url_for
from werkzeug import secure_filename
from . import main, content_configuration, validation_tools


@main.route('/')
def index():
    return render_template("index.html", **get_template_data())


@main.route('/service')
def find():
    return redirect("/service/" + request.args.get("service_id"))


@main.route('/service/<service_id>')
def view(service_id):
    service_data = get_service_json(service_id)
    template_data = get_template_data({
        "sections": content_configuration.get_sections(),
        "service_data": service_data
    })
    template_data["service_data"]["id_split"] = re.findall(
        "....", str(template_data["service_data"]["id"])
    )
    return render_template("view_service.html", **template_data)


@main.route('/service/<service_id>/edit/<section>')
def edit(service_id, section):
    template_data = get_template_data({
        "section": content_configuration.get_section(section),
        "service_data": get_service_json(service_id)
    })
    return render_template("edit_section.html", **template_data)


@main.route('/service/<service_id>/edit/<section>', methods=['POST'])
def update(service_id, section):

    posted_data = dict(request.form, **request.files)
    validations = validation_tools.Validations()
    errors = {}
    successes = {}  # just for debugging

    for question_id in posted_data:
        content = content_configuration.get_question(question_id)
        for validation_rule in content["validations"]:
            valid = validations.save_file(  # TODO: validation_rule["name"]
                question_id,
                posted_data[question_id]
            )
            if not valid:
                errors[question_id] = validation_rule["message"]
                break
            else:
                successes[question_id] = "all OK"  # just for debugging
            break  # TODO: loop through every validation rule

    template_data = get_template_data({
        "edits_submitted": dict(request.form, **request.files),
        "service_id": service_id,
        "errors": errors,
        "successes": successes
    })

    if len(errors):
        return render_template("confirm.html", **template_data)
    else:
        return redirect("/service/" + service_id)


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
    return json.loads(response.content)["services"]


def get_template_data(merged_with=[]):
    return dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
