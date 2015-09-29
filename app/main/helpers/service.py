import re

from flask import abort

from dmutils.s3 import S3
from dmutils.content_loader import PRICE_FIELDS
from dmutils.documents import filter_empty_files, validate_documents, upload_document


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


def has_changes_to_save(section, service, update_data):
    return (
        update_data_hash_changed(service, update_data)
        or
        service_is_missing_questions(section, service)
    )


def update_data_hash_changed(service, update_data):
    return any(service.get(key) != update_data[key] for key in update_data)


def service_is_missing_questions(section, service):
    return any(question['id'] not in service for question in section.questions)


def _filter_keys(data, keys):
    """Return a dictionary filtered by a list of keys

    >>> _filter_keys({'a': 1, 'b': 2}, ['a'])
    {'a': 1}
    """
    key_set = set(keys) & set(data)
    return {key: data[key] for key in key_set}


def upload_documents(service, request_files, section, bucket, document_url):
    request_files = request_files.to_dict(flat=True)
    files = _filter_keys(request_files, section.get_field_names())
    files = filter_empty_files(files)
    errors = validate_documents(files)

    if errors:
        return None, errors

    if len(files) == 0:
        return {}, {}

    uploader = S3(bucket)

    for field, contents in files.items():
        url = upload_document(
            uploader, document_url, service, field, contents)

        if not url:
            errors[field] = 'file_can_be_saved'
        else:
            files[field] = url

    return files, errors
