# coding=utf-8
from unittest import TestCase

from app.main.helpers.sum_counts import _label_and_count, _sum_counts, _find


class TestLabelAndCount(TestCase):
    def test_formatting(self):
        assert _label_and_count({}, {
            'one': {
                'filter_one': None
            },
            'two': {
                'filter_one': False,
                'filter_two': True,
            },
            'three': {
                'filter_two': True
            }
        }, created_at='today') == {'created_at': 'today', 'one': 0, 'two': 0, 'three': 0}


class TestSumCounts(TestCase):
    def test_summing_without_filtering(self):
        assert _sum_counts([
            {'count': 1},
            {'count': 2},
            {'count': 3},
            {'count': 4}
        ]) == 10

    def test_summing_filtering_on_one_attribute(self):
        assert _sum_counts(
            [
                {'count': 1, 'include': False},
                {'count': 2, 'include': True},
                {'count': 3, 'include': True},
                {'count': 4, 'include': False}
            ],
            {'include': True},
        ) == 5

    def test_summing_filtering_on_multiple_attributes(self):
        assert _sum_counts(
            [
                {'count': 1, 'include': False, 'exclude': True},
                {'count': 2, 'include': True, 'exclude': False},
                {'count': 3, 'include': True, 'exclude': True},
                {'count': 4, 'include': False, 'exclude': False}
            ],
            {
                'include': True,
                'exclude': False,
            },
        ) == 2

    def test_summing_filtering_on_various_acceptable_attributes(self):
        assert _sum_counts(
            [
                {'count': 1, 'colour': 'cyan'},
                {'count': 2, 'colour': 'yellow'},
                {'count': 3, 'colour': 'magenta'},
                {'count': 4, 'colour': 'black'}
            ],
            {'colour': ['cyan', 'yellow', 'magenta']},
        ) == 6

    def test_summing_by_different_column(self):
        assert _sum_counts(
            [
                {'count': 1, 'new_count': 10},
                {'count': 2, 'new_count': 20},
                {'count': 3, 'new_count': 30},
                {'count': 4, 'new_count': 40}
            ],
            sum_by='new_count',
        ) == 100


class TestFind(TestCase):
    def test_find_string(self):
        assert _find('word', 'word')
        assert not _find('drow', 'word')

    def test_doesnt_match_substring(self):
        assert not _find('word', 'word1234')

    def test_find_number(self):
        assert _find(99, 99)
        assert not _find(99, 99.99)

    def test_find_none(self):
        assert _find(None, None)
        assert not _find(None, 'None')

    def test_find_boolean(self):
        assert _find(True, True)
        assert not _find(False, True)

    def test_find_in_list(self):
        assert _find('yes', [True, 0, 'yes'])
        assert not _find('no', [True, 0, 'yes'])
