# coding=utf-8
from unittest import TestCase
from nose.tools import assert_equal

from app.main.helpers.sum_counts import label_and_count, _sum_counts


class TestLabelAndCount(TestCase):
    def test_formatting(self):
        assert_equal(
            label_and_count({}, {
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
            }),
            [{'one': 0, 'two': 0, 'three': 0}]
        )


class TestSumCounts(TestCase):
    def test_summing_without_filtering(self):
        assert_equal(
            _sum_counts([
                {'count': 1},
                {'count': 2},
                {'count': 3},
                {'count': 4}
            ]),
            10
        )

    def test_summing_filtering_on_one_attribute(self):
        assert_equal(
            _sum_counts([
                {'count': 1, 'include': False},
                {'count': 2, 'include': True},
                {'count': 3, 'include': True},
                {'count': 4, 'include': False}
            ], {
                'include': True
            }),
            5
        )

    def test_summing_filtering_on_multiple_attributes(self):
        assert_equal(
            _sum_counts([
                {'count': 1, 'include': False, 'exclude': True},
                {'count': 2, 'include': True, 'exclude': False},
                {'count': 3, 'include': True, 'exclude': True},
                {'count': 4, 'include': False, 'exclude': False}
            ], {
                'include': True,
                'exclude': False
            }),
            2
        )

    def test_summing_by_different_column(self):
        assert_equal(
            _sum_counts([
                {'count': 1, 'new_count': 10},
                {'count': 2, 'new_count': 20},
                {'count': 3, 'new_count': 30},
                {'count': 4, 'new_count': 40}
            ], sum_by='new_count'),
            100
        )
