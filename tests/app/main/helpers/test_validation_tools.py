import unittest

import mock
from app.main.helpers.s3 import S3ResponseError
from app.main.helpers.validation_tools import Validate


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.service = {
            'id': 1,
            'supplierId': 2,
        }
        self.data = {}
        self.content = {}
        self.uploader = mock.Mock()

        self.validate = Validate(
            content=mock.Mock(),
            service=self.service,
            posted_data=self.data,
            uploader=self.uploader
        )

        self.validate.content.get_question = lambda key: self.content[key]

    def set_question(self, question_id, data, *validations, **kwargs):
        self.data[question_id] = data
        if 'value' in kwargs:
            self.service[question_id] = kwargs['value']
        self.content[question_id] = {'validations': validations}

    def test_validate_empty(self):
        self.assertEquals(self.validate.errors, {})

    def test_validate_empty_question(self):
        self.set_question('q1', mock_file('a', 0))
        self.assertEquals(self.validate.errors, {})

    def test_validate_non_empty_answer_required(self):
        self.set_question(
            'q1', mock_file('a', 1),
            {'name': 'answer_required', 'message': 'failed'}
        )
        self.assertEquals(self.validate.errors, {})

    def test_validate_empty_answer_required(self):
        self.set_question(
            'q1', mock_file('a.pdf', 0),
            {'name': 'answer_required', 'message': 'failed'}
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_validate_empty_answer_required_previous_value(self):
        self.set_question(
            'q1', mock_file('a.pdf', 0),
            {'name': 'answer_required', 'message': 'failed'},
            value='b.pdf',
        )
        self.assertEquals(self.validate.errors, {})

    def test_incorrect_document_format(self):
        self.set_question(
            'q1', mock_file('a.txt', 1),
            {'name': 'file_is_open_document_format', 'message': 'failed'}
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_incorrect_file_size(self):
        self.set_question(
            'q1', mock_file('a.pdf', 5400001),
            {'name': 'file_is_less_than_5mb', 'message': 'failed'}
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_list_of_validations(self):
        self.set_question(
            'q1', mock_file('a.pdf', 1),
            {'name': 'file_is_open_document_format', 'message': 'failed'},
            {'name': 'file_is_less_than_5mb', 'message': 'failed'},
            value='b.pdf'
        )
        self.assertEquals(self.validate.errors, {})

    def test_file_save(self):
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1, 'pricingDocumentURL'),
            {'name': 'file_can_be_saved', 'message': 'failed'},
            value='b.pdf'
        )

        self.assertEquals(self.validate.errors, {})
        self.uploader.save.assert_called_once_with(
            'documents/2/1-pricing-document.pdf',
            self.data['pricingDocumentURL'],
            'b.pdf'
        )

        self.assertEquals(self.validate.clean_data, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document.pdf',  # noqa
        })

    def test_failed_file_upload(self):
        self.uploader.save.side_effect = S3ResponseError(403, 'Forbidden')
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1, 'pricingDocumentURL'),
            {'name': 'file_can_be_saved', 'message': 'failed'},
            value='b.pdf'
        )

        self.assertEquals(self.validate.errors, {
            'pricingDocumentURL': 'failed'
        })

        self.assertEquals(self.validate.clean_data, {})

    def test_field_with_no_previous_value(self):
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1),
            {'name': 'answer_required', 'message': 'failed'},
            {'name': 'file_is_open_document_format', 'message': 'failed'},
            {'name': 'file_is_less_than_5mb', 'message': 'failed'},
            {'name': 'file_can_be_saved', 'message': 'failed'},
            value=None
        )
        self.assertEquals(self.validate.errors, {})

    def test_multiple_fields_list_of_validations(self):
        validations = [
            {'name': 'file_is_open_document_format', 'message': 'format'},
            {'name': 'file_is_less_than_5mb', 'message': 'size'},
        ]

        self.set_question('q0', mock_file('a.pdf', 1),
                          value='b.pdf', *validations)
        self.set_question('q1', mock_file('a.txt', 1),
                          value='b.pdf', *validations)
        self.set_question('q2', mock_file('a.pdf', 5400001),
                          value='b.pdf', *validations)
        self.set_question('q3', mock_file('a.txt', 5400001),
                          value='b.pdf', *validations)

        self.assertEquals(self.validate.errors, {
            'q1': 'format',
            'q2': 'size',
            'q3': 'format'
        })


def mock_file(filename, length, name=None):
    mock_file = mock.MagicMock()
    mock_file.read.return_value = '*' * length
    mock_file.filename = filename
    mock_file.name = name

    return mock_file
