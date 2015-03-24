import os.path
import urlparse

from .. import main


class Validate(object):
    def __init__(self, content, service, posted_data, uploader=None):
        self.content = content
        self.service = service
        self.posted_data = posted_data
        self.uploader = uploader
        self.clean_data = {}
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
            if question_id in self.service:
                return

        for rule in question_content["validations"]:
            if not self.test(question_id, question, rule["name"]):
                return rule["message"]

        # TODO We can't update file URLs until we have the write API,
        # so uploaded file must have the same extension as the
        # current one for now
        current_extension = get_extension(self.service.get(question_id, ''))
        if get_extension(question.filename) != current_extension:
            return u"Uploaded file format should be: %s" % current_extension

    def test(self, question_id, question, rule):
        if not hasattr(self, rule):
            raise ValueError("Validation rule " + rule + " not found")
        return getattr(self, rule)(question_id, question)

    def answer_required(self, question_id, question):
        not_empty = len(question.read(1)) > 0
        question.seek(0)
        return not_empty

    def file_can_be_saved(self, question_id, question):
        file_name = self._generate_file_name(question)
        file_path = 'documents/{}'.format(
            self.service['supplierId'],
        )

        self.uploader.save(
            file_path,
            file_name,
            question
        )

        full_url = urlparse.urljoin(
            main.config['DOCUMENTS_URL'],
            "{}/{}".format(file_path, file_name)
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

    def _generate_file_name(self, question):
        ID_TO_FILE_NAME_SUFFIX = {
            'serviceDefinitionDocumentURL': 'service-definition-document',
            'termsAndConditionsDocumentURL': 'terms-and-conditions',
            'sfiaRateDocumentURL': 'sfia-rate-card',
            'pricingDocumentURL': 'pricing-document',
        }
        extension = get_extension(question.filename)

        return '{}-{}{}'.format(
            self.service['id'],
            ID_TO_FILE_NAME_SUFFIX[question.name],
            extension
        )


def get_extension(filename):
    file_name, file_extension = os.path.splitext(filename)
    return file_extension.lower()
