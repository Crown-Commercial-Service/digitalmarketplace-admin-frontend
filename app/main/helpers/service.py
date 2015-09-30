import re

from flask import abort

from dmutils.s3 import S3
from dmutils.content_loader import PRICE_FIELDS
from dmutils.documents import filter_empty_files, validate_documents, upload_document


def parse_document_upload_time(data):
    match = re.search("(\d{4}-\d{2}-\d{2}-\d{2}\d{2})\..{2,3}$", data)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H%M")


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
