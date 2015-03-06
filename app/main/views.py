import os
import requests
import re
from flask import render_template, request, redirect, url_for
from . import main
from .helpers.validation_tools import Validate
from .helpers.content import ContentLoader
from .helpers.service import ServiceLoader
from .helpers.auth import requires_auth


service = ServiceLoader(
    os.getenv('DM_API_URL'),
    os.getenv('DM_ADMIN_FRONTEND_API_AUTH_TOKEN')
)
content = ContentLoader(
    "app/section_order.yml",
    "bower_components/digital-marketplace-ssp-content/g6/"
)


@main.route('/')
@requires_auth
def index():
    return render_template("index.html", **get_template_data())


@main.route('/service')
@requires_auth
def find():
    return redirect("/service/" + request.args.get("service_id"))


@main.route('/service/<service_id>')
@requires_auth
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
@requires_auth
def edit(service_id, section):
    template_data = get_template_data({
        "section": content.get_section(section),
        "service_data": service.get(service_id).data
    })
    return render_template("edit_section.html", **template_data)


@main.route('/service/<service_id>/edit/<section>', methods=['POST'])
@requires_auth
def update(service_id, section):

    service.get(service_id)
    posted_data = dict(request.form, **request.files)
    errors = {}

    for question_id in posted_data:
        validate = Validate(posted_data[question_id])
        for rule in content.get_question(question_id)["validations"]:
            if not validate.test("answer_required"):
                if "optional" in content.get_question(question_id):
                    break  # question is optional
                if question_id in service.data:
                    break  # file has previously been uploaded
            if not validate.test(rule["name"]):
                errors[question_id] = rule["message"]
                break
        if question_id not in errors:
            service.set(question_id, "new value")

    if len(errors):
        return render_template("edit_section.html", **get_template_data({
            "section": content.get_section(section),
            "service_data": service.get(service_id).data,
            "edits_submitted": posted_data,
            "service_id": service_id,
            "errors": errors
        }))
    else:
        service.post()
        return redirect("/service/" + service_id)


def get_template_data(merged_with={}):
    return dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
