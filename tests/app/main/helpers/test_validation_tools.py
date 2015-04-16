# coding=utf-8

import unittest
import datetime

import mock
from app.main.helpers.s3 import S3ResponseError
from app.main.helpers.validation_tools import Validate, generate_file_name


class TestGenerateFilename(unittest.TestCase):
    def test_filename_format(self):
        self.assertEquals(
            'documents/2/1-pricing-document-123.pdf',
            generate_file_name(
                2, 1,
                'pricingDocumentURL', 'test.pdf',
                suffix='123'
            ))

    def test_default_suffix_is_datetime(self):
        now = datetime.datetime(2015, 1, 2, 3, 4, 5, 6)

        with mock.patch.object(datetime, 'datetime',
                               mock.Mock(wraps=datetime.datetime)) as patched:
            patched.utcnow.return_value = now
            self.assertEquals(
                'documents/2/1-pricing-document-2015-01-02-0304.pdf',
                generate_file_name(
                    2, 1,
                    'pricingDocumentURL', 'test.pdf',
                ))


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.service = {
            'id': 1,
            'supplierId': 2,
        }
        self.data = {}
        self.content = {}
        self.uploader = mock.Mock()

        self.default_suffix_patch = mock.patch(
            'app.main.helpers.validation_tools.default_file_suffix',
            return_value='2015-01-01-1200'
        ).start()

        self.validate = Validate(
            content=mock.Mock(),
            service=self.service,
            posted_data=self.data,
            uploader=self.uploader
        )

        self.validate.content.get_question = lambda key: self.content[key]

    def tearDown(self):
        self.default_suffix_patch.stop()

    def set_question(self, question_id, data, content, **kwargs):
        self.data[question_id] = data
        if 'value' in kwargs:
            self.service[question_id] = kwargs['value']
        self.content[question_id] = content

        self.validate.validate()

    def test_validate_empty(self):
        self.validate.validate()
        self.assertEquals(self.validate.errors, {})

    def test_validate_empty_question(self):
        self.set_question('q1', mock_file('a', 0), {'validations': []})
        self.assertEquals(self.validate.errors, {})

    def test_validate_non_empty_answer_required(self):
        self.set_question(
            'q1', mock_file('a', 1),
            {
                'type': 'upload',
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_validate_text_without_validators(self):
        self.set_question(
            'q1', 'value',
            {
                'optional': True,
                'validations': []
            }
        )

        self.assertEquals(self.validate.errors, {})
        self.assertEquals(self.validate.clean_data['q1'], 'value')

    def test_validate_empty_upload_optional(self):
        self.set_question(
            'q1', mock_file('a.pdf', 0),
            {
                'type': 'upload',
                'optional': True,
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            }
        )

        self.assertEquals(self.validate.errors, {})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_validate_empty_upload_optional_with_previous_value(self):
        self.set_question(
            'q2', mock_file('a.pdf', 0),
            {
                'type': 'upload',
                'optional': True,
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            },
            value='b.pdf',
        )
        self.assertEquals(self.validate.errors, {})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_validate_empty_upload_not_optional(self):
        self.set_question(
            'q1', mock_file('a.pdf', 0),
            {
                'type': 'upload',
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_validate_empty_upload_not_optional_with_previous_value(self):
        self.set_question(
            'q2', mock_file('a.pdf', 0),
            {
                'type': 'upload',
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            },
            value='b.pdf',
        )
        self.assertEquals(self.validate.errors, {})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_validate_empty_text_optional(self):
        self.set_question(
            'q1', '',
            {
                'optional': True,
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            }
        )

        self.assertEquals(self.validate.errors, {})
        self.assertEquals(self.validate.clean_data['q1'], '')

    def test_validate_empty_text_optional_with_previous_value(self):
        self.set_question(
            'q2', '',
            {
                'optional': True,
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            },
            value='Previous value',
        )
        self.assertEquals(self.validate.errors, {})
        self.assertEquals(self.validate.clean_data['q2'], '')

    def test_validate_empty_text_not_optional(self):
        self.set_question(
            'q1', '',
            {
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_validate_empty_text_not_optional_with_previous_value(self):
        self.set_question(
            'q2', '',
            {
                'validations': [{
                    'name': 'answer_required', 'message': 'failed'
                }]
            },
            value='Previous value',
        )
        self.assertEquals(self.validate.errors, {'q2': 'failed'})
        self.assertNotIn('q1', self.validate.clean_data)

    def test_incorrect_document_format(self):
        self.set_question(
            'q1', mock_file('a.txt', 1),
            {
                'type': 'upload',
                'validations': [{
                    'name': 'file_is_open_document_format', 'message': 'failed'
                }]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_incorrect_file_size(self):
        self.set_question(
            'q1', mock_file('a.pdf', 5400001),
            {
                'type': 'upload',
                'validations': [{
                    'name': 'file_is_less_than_5mb', 'message': 'failed'
                }]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_list_of_validations(self):
        self.set_question(
            'q1', mock_file('a.pdf', 1),
            {
                'type': 'upload',
                'validations': [
                    {
                        'name': 'file_is_open_document_format',
                        'message': 'failed'
                    },
                    {
                        'name': 'file_is_less_than_5mb', 'message': 'failed'
                    },
                ]
            },
            value='b.pdf'
        )
        self.assertEquals(self.validate.errors, {})

    def test_file_save(self):
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1, 'pricingDocumentURL'),
            {
                'type': 'upload',
                'validations': [
                    {'name': 'file_can_be_saved', 'message': 'failed'},
                ]
            },
            value='b.pdf'
        )

        self.assertEquals(self.validate.errors, {})

        self.uploader.save.assert_called_once_with(
            'documents/2/1-pricing-document-2015-01-01-1200.pdf',
            self.data['pricingDocumentURL']
        )

        self.assertEquals(self.validate.clean_data, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
        })

    def test_failed_file_upload(self):
        self.uploader.save.side_effect = S3ResponseError(403, 'Forbidden')
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1, 'pricingDocumentURL'),
            {
                'type': 'upload',
                'validations': [
                    {'name': 'file_can_be_saved', 'message': 'failed'},
                ]
            },
            value='b.pdf'
        )

        self.assertEquals(self.validate.errors, {
            'pricingDocumentURL': 'failed'
        })

        self.assertEquals(self.validate.clean_data, {})

    def test_field_with_no_previous_value(self):
        self.set_question(
            'pricingDocumentURL', mock_file('a.pdf', 1),
            {
                'type': 'upload',
                'validations': [
                    {'name': 'answer_required', 'message': 'failed'},
                    {
                        'name': 'file_is_open_document_format',
                        'message': 'failed'
                    },
                    {'name': 'file_is_less_than_5mb', 'message': 'failed'},
                    {'name': 'file_can_be_saved', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_multiple_fields_list_of_validations(self):
        content = {
            'type': 'upload',
            'validations': [
                {'name': 'file_is_open_document_format', 'message': 'format'},
                {'name': 'file_is_less_than_5mb', 'message': 'size'}
            ]
        }

        self.set_question('q0', mock_file('a.pdf', 1), content,
                          value='b.pdf')
        self.set_question('q1', mock_file('a.txt', 1), content,
                          value='b.pdf')
        self.set_question('q2', mock_file('a.pdf', 5400001), content,
                          value='b.pdf')
        self.set_question('q3', mock_file('a.txt', 5400001), content,
                          value='b.pdf')

        self.assertEquals(self.validate.errors, {
            'q1': 'format',
            'q2': 'size',
            'q3': 'format'
        })

    def test_min_price_specified(self):
        self.set_question(
            'q1', ['1'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'no_min_price_specified', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_min_price_not_specified(self):
        self.set_question(
            'q1', [''],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'no_min_price_specified', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_prices_are_numbers(self):
        self.set_question(
            'q1', ['1', '2'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'min_price_not_a_number', 'message': 'failed'},
                    {'name': 'max_price_not_a_number', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_min_price_isnt_a_number(self):
        self.set_question(
            'q1', ['£1', '2'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'min_price_not_a_number', 'message': 'failed'},
                    {'name': 'max_price_not_a_number', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_max_price_isnt_a_number(self):
        self.set_question(
            'q1', ['1', '£2'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'min_price_not_a_number', 'message': 'failed'},
                    {'name': 'max_price_not_a_number', 'message': 'failed'},
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_max_price_is_less_than_min(self):
        self.set_question(
            'q1', ['2', '1'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'max_less_than_min', 'message': 'failed'}
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_max_price_is_greater_than_min(self):
        self.set_question(
            'q1', ['1', '2'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'max_less_than_min', 'message': 'failed'}
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_max_price_is_empty(self):
        self.set_question(
            'q1', ['1', ''],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'max_less_than_min', 'message': 'failed'}
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_price_unit_is_missing(self):
        self.set_question(
            'q1', ['1', '2', ''],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'no_unit_specified', 'message': 'failed'}
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_price_unit_is_present(self):
        self.set_question(
            'q1', ['1', '2', 'Virtual machine'],
            {
                'type': 'pricing',
                'validations': [
                    {'name': 'no_unit_specified', 'message': 'failed'}
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_price_string_can_be_composed(self):
        self.set_question(
            'q2', ['1', '2', 'Instance', 'Year'],
            {
                'type': 'pricing',
                'validations': [
                    {
                        'name': 'price_string_can_be_composed',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})
        self.assertEquals(
            self.validate.clean_data.get('priceString'),
            u'£1 to £2 per instance per year'
        )

    def test_string_over_100_characters(self):
        self.set_question(
            'q1', " ".join('a' for i in range(0, 101)),
            {
                'type': 'text',
                'validations': [
                    {
                        'name': 'under_100_characters',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_string_under_100_characters(self):
        self.set_question(
            'q1', "".join('a' for i in range(0, 100)),
            {
                'type': 'text',
                'validations': [
                    {
                        'name': 'under_100_characters',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_string_over_50_words(self):
        self.set_question(
            'q1', " ".join(str(i) for i in range(0, 51)),
            {
                'type': 'text',
                'validations': [
                    {
                        'name': 'under_50_words',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_string_under_50_words(self):
        self.set_question(
            'q1', " ".join(str(i) for i in range(0, 50)),
            {
                'type': 'text',
                'validations': [
                    {
                        'name': 'under_50_words',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_list_with_1_item(self):
        self.set_question(
            'q1', ["1"],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'under_10_items',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_list_with_10_items(self):
        self.set_question(
            'q1', ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'under_10_items',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_list_with_11_items(self):
        self.set_question(
            'q1', ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'under_10_items',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})

    def test_list_with_empty_items(self):
        self.set_question(
            'q1', [
                "something",
                "",
                "something",
                "",
                "something"
            ],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'under_10_items',
                        'message': 'failed'
                    }
                ]
            }
        )
        errors = self.validate.errors
        self.assertEquals(
            self.validate.clean_data['q1'],
            ["something", "something", "something"]
        )

    def test_list_with_short_items(self):
        self.set_question(
            'q1', [
                "one two three four five six seven eight nine ten" for i in range(0, 3)  # noqa
            ],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'items_under_10_words_each',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {})

    def test_list_with_long_items(self):
        self.set_question(
            'q1', [
                "one two three four five six seven eight nine ten eleven" for i in range(0, 3)  # noqa
            ],
            {
                'type': 'list',
                'validations': [
                    {
                        'name': 'items_under_10_words_each',
                        'message': 'failed'
                    }
                ]
            }
        )
        self.assertEquals(self.validate.errors, {'q1': 'failed'})


def mock_file(filename, length, name=None):
    mock_file = mock.MagicMock()
    mock_file.read.return_value = '*' * length
    mock_file.filename = filename
    mock_file.name = name

    return mock_file
