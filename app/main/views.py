import os
import requests
import re
from flask import render_template, request, redirect, url_for
from . import main
from helpers.validation_tools import Validate
from helpers.content import Content_loader
from helpers.service import Service_loader


service = Service_loader(
    os.getenv('DM_API_URL'),
    os.getenv('DM_API_BEARER')
)
content = Content_loader(
    "app/section_order.yml",
    "bower_components/digital-marketplace-ssp-content/g6/"
)


@main.route('/')
def index():
    return render_template("index.html", **get_template_data())


@main.route('/service')
def find():
    return redirect("/service/" + request.args.get("service_id"))


@main.route('/service/<service_id>')
def view(service_id):
    template_data = get_template_data({
        "sections": content.sections,
        "service_data": service.get(service_id).data
    })
    template_data["service_data"]["id_split"] = re.findall(
        "....", str(template_data["service_data"]["id"])
    )
    return render_template("view_service.html", **template_data)


@main.route('/service/<service_id>/edit/<section>')
def edit(service_id, section):
    template_data = get_template_data({
        "section": content.get_section(section),
        "service_data": service.get(service_id).data
    })
    return render_template("edit_section.html", **template_data)


@main.route('/service/<service_id>/edit/<section>', methods=['POST'])
def update(service_id, section):

    service.get(service_id)
    posted_data = dict(request.form, **request.files)
    errors = {}
    successes = {}  # just for debugging

    for question_id in posted_data:
        validate = Validate(posted_data[question_id])
        for rule in content.get_question(question_id)["validations"]:
            if not validate.test(rule["name"]):
                print "error!"
                errors[question_id] = rule["message"]
                break
        if question_id not in errors:
            successes[question_id] = "all OK"  # just for debugging
            service.set(question_id, "new value")

    template_data = get_template_data({
        "edits_submitted": posted_data,
        "service_id": service_id,
        "errors": errors,
        "successes": successes
    })

    if len(errors):
        service.post()  # Debug--shouldn't post for real if there are errors
        return render_template("confirm.html", **template_data)
    else:
        service.post()
        return redirect("/service/" + service_id)


def get_template_data(merged_with={}):
    return dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
