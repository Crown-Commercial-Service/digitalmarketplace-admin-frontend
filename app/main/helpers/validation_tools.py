import datetime
import os.path
import six
import re
import locale
import werkzeug.datastructures

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from .. import main
from .s3 import S3ResponseError


class Validate(object):
    def __init__(self, content, service, posted_data, uploader=None):
        self.content = content
        self.service = service
        self.posted_data = posted_data
        self.uploader = uploader
        self.clean_data = {}
        self.dirty_data = {}
        self._errors = None

    @property
    def errors(self):
        if self._errors is not None:
            return self._errors
        errors = {}
        for question_id in self.posted_data:
            question_errors = self.question_errors(question_id)
            if question_errors:
                errors[question_id] = question_errors

        self._errors = errors
        return errors

    def question_errors(self, question_id):
        question = self.posted_data[question_id]
        question_content = self.content.get_question(question_id)

        if not self.test(question_id, question, "answer_required"):
            if "optional" in question_content:
                return
            # File has previously been uploaded
            if (
                question_id in self.service and
                'upload' == question_content.get('type')
            ):
                return

        for rule in question_content["validations"]:
            if not self.test(question_id, question, rule["name"]):
                return rule["message"]

    def test(self, question_id, question, rule):
        if not hasattr(self, rule):
            raise ValueError("Validation rule " + rule + " not found")
        return getattr(self, rule)(question_id, question)

    def answer_required(self, question_id, question):
        content = self.content.get_question(question_id)
        if isinstance(question, list):
            question_as_string = "".join(question).strip()
            return len(question_as_string)
        elif 'upload' == content.get('type'):
            return self.file_has_been_uploaded(question_id, question)
        elif isinstance(question, six.string_types) and not empty(question):
            self.clean_data[question_id] = question
            return True

    def file_has_been_uploaded(self, question_id, question):
        not_empty = len(question.read(1)) > 0
        question.seek(0)
        return not_empty

    def file_can_be_saved(self, question_id, question):

        file_path = generate_file_name(
            self.service['supplierId'],
            self.service['id'],
            question_id,
            question.filename
        )

        try:
            self.uploader.save(file_path, question)
        except S3ResponseError:
            return False

        full_url = urlparse.urljoin(
            main.config['DOCUMENTS_URL'],
            file_path
        )

        self.clean_data[question_id] = full_url

        return True

    def file_is_less_than_5mb(self, question_id, question):
        size_limit = 5400000
        below_size_limit = len(question.read(size_limit)) < size_limit
        question.seek(0)

        return below_size_limit

    def file_is_open_document_format(self, question_id, question):

        return get_extension(question.filename) in [
            ".pdf", ".pda", ".odt", ".ods", ".odp"
        ]

    def no_min_price_specified(self, question_id, question):
        min_price = question[0]
        self.dirty_data["priceMin"] = min_price
        return not empty(min_price)

    def min_price_not_a_number(self, question_id, question):
        min_price = question[0]
        self.dirty_data["priceMin"] = min_price
        if is_a_float(min_price) and less_than_5_decimal_places(min_price):
            return True
        return False

    def max_price_not_a_number(self, question_id, question):
        max_price = question[1]
        self.dirty_data["priceMax"] = max_price
        if empty(max_price):
            return True
        if is_a_float(max_price) and less_than_5_decimal_places(max_price):
            return True
        return False

    def max_less_than_min(self, question_id, question):
        min_price, max_price = question[0:2]
        if empty(max_price):
            return True
        return float(max_price) > float(min_price)

    def no_unit_specified(self, question_id, question):
        price_unit = question[2]
        self.dirty_data["priceUnit"] = price_unit
        return not empty(price_unit)

    def price_string_can_be_composed(self, question_id, question):
        min_price, max_price, price_unit, price_interval = question
        price_string = "£" + min_price
        self.clean_data["priceMin"] = format_price_to_number(min_price)
        if not empty(max_price):
            price_string = price_string + " to £" + question[1]
            self.clean_data["priceMax"] = format_price_to_number(max_price)
        else:
            self.clean_data["priceMax"] = None  # This doesn't work -- API
        price_string = price_string + " per "
        price_string = price_string + price_unit.lower()
        self.clean_data["priceUnit"] = price_unit
        if not empty(price_interval):
            price_string = price_string + " per " + price_interval.lower()
            self.clean_data["priceInterval"] = price_interval
        else:
            self.clean_data["priceInterval"] = ""
        self.clean_data["priceString"] = price_string
        return True


def generate_file_name(supplier_id, service_id, question_id, filename,
                       suffix=None):
    if suffix is None:
        suffix = default_file_suffix()

    ID_TO_FILE_NAME_SUFFIX = {
        'serviceDefinitionDocumentURL': 'service-definition-document',
        'termsAndConditionsDocumentURL': 'terms-and-conditions',
        'sfiaRateDocumentURL': 'sfia-rate-card',
        'pricingDocumentURL': 'pricing-document',
    }

    return 'documents/{}/{}-{}-{}{}'.format(
        supplier_id,
        service_id,
        ID_TO_FILE_NAME_SUFFIX[question_id],
        suffix,
        get_extension(filename)
    )


def default_file_suffix():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d-%H%M")


def get_extension(filename):
    file_name, file_extension = os.path.splitext(filename)
    return file_extension.lower()


def is_a_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def less_than_5_decimal_places(number):
    return re.match(r'^[0-9]+(\.\d{1,5})?$', number)


def format_price_to_number(number):
    try:
        int(number)
        return int(number)
    except ValueError:
        return float(number)


def empty(string):
    return 0 == len(string.strip())
