import unittest

import mock
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

    def test_validate_empty(self):
        self.assertEquals(self.validate.errors, {})

    def test_validate_empty_question(self):
        self.data['q1'] = mock_file('a', 0)
        self.content['q1'] = {'validations': []}
        self.assertEquals(self.validate.errors, {})

    def test_validate_non_empty_answer_required(self):
        self.data['q1'] = mock_file('a', 1)
        self.content['q1'] = {
            'validations': [
                {'name': 'answer_required', 'message': 'failed'}
            ]
        }
        self.assertEquals(self.validate.errors, {})

    def test_validate_empty_answer_required(self):
        self.data['q1'] = mock_file('a.pdf', 0)
        self.content['q1'] = {
            'validations': [
                {'name': 'answer_required', 'message': 'failed'}
            ]
        }
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_incorrect_document_format(self):
        self.data['q1'] = mock_file('a.txt', 1)
        self.content['q1'] = {
            'validations': [
                {'name': 'file_is_open_document_format', 'message': 'failed'}
            ]
        }
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_incorrect_file_size(self):
        self.data['q1'] = mock_file('a.pdf', 5400001)
        self.content['q1'] = {
            'validations': [
                {'name': 'file_is_less_than_5mb', 'message': 'failed'}
            ]
        }
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_list_of_validations(self):
        self.data['q1'] = mock_file('a.pdf', 1)
        self.service['q1'] = 'b.pdf'
        self.content['q1'] = {
            'validations': [
                {'name': 'file_is_open_document_format', 'message': 'failed'},
                {'name': 'file_is_less_than_5mb', 'message': 'failed'},
            ]
        }
        self.assertEquals(self.validate.errors, {})

    def test_file_save(self):
        self.data['pricingDocumentURL'] = mock_file('a.pdf', 1,
                                                    'pricingDocumentURL')
        self.service['pricingDocumentURL'] = 'b.pdf'
        self.content['pricingDocumentURL'] = {
            'validations': [
                {'name': 'file_can_be_saved', 'message': 'failed'},
            ]
        }

        self.assertEquals(self.validate.errors, {})
        self.uploader.save.assert_called_once_with(
            'documents/2/1-pricing-document.pdf',
            self.data['pricingDocumentURL'],
            'b.pdf'
        )

        self.assertEquals(self.validate.clean_data, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document.pdf',  # noqa
        })

    def test_multiple_fields_list_of_validations(self):
        self.data.update({
            'q0': mock_file('a.pdf', 1),
            'q1': mock_file('a.txt', 1),
            'q2': mock_file('a.pdf', 5400001),
            'q3': mock_file('a.txt', 5400001),
        })
        self.service.update({
            'q0': 'b.pdf',
            'q1': 'b.pdf',
            'q2': 'b.pdf',
            'q3': 'b.pdf',
        })
        validations = [
            {'name': 'file_is_open_document_format', 'message': 'format'},
            {'name': 'file_is_less_than_5mb', 'message': 'size'},
        ]
        self.content.update({
            'q0': {'validations': validations},
            'q1': {'validations': validations},
            'q2': {'validations': validations},
            'q3': {'validations': validations},
        })

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
