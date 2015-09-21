import re

from flask import abort

from dmutils.content_loader import PRICE_FIELDS


def get_section_error_messages(service_content, errors, lot):
    errors_map = {}
    for error_field, message_key in errors.items():
        question_key = error_field
        if error_field == '_form':
            abort(400, "Submitted data was not in a valid format")
        elif error_field == 'serviceTypes':
            error_field = 'serviceTypes{}'.format(lot)
            question_key = error_field
        elif error_field in PRICE_FIELDS:
            message_key = _rewrite_pricing_error_key(error_field, message_key)
            error_field = 'priceString'
            question_key = error_field
        elif message_key == 'assurance_required':
            question_key = error_field + '--assurance'

        validation_message = get_error_message(error_field, message_key, service_content)

        errors_map[question_key] = {
            'input_name': question_key,
            'question': service_content.get_question(error_field)['question'],
            'message': validation_message
        }
    return errors_map


def get_error_message(field, message_key, content):
    validations = [
        validation for validation in content.get_question(field)['validations']
        if validation['name'] == message_key]

    if len(validations):
        return validations[0]['message']
    else:
        return 'There was a problem with the answer to this question'


def parse_document_upload_time(data):
    match = re.search("(\d{4}-\d{2}-\d{2}-\d{2}\d{2})\..{2,3}$", data)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H%M")
