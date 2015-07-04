import unittest
from app.main.helpers.diff_tools import StringDiffTool, ListDiffTool
from flask import Markup
from abc import ABCMeta, abstractmethod


class TestBaseDiffTool():

    maxDiff = None

    __metaclass__ = ABCMeta

    @abstractmethod
    def _get_diff_tool(self, revision_1, revision_2, if_unchanged):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _get_original_line_from_revision(self, words):

        return " ".join([word[2:] for word in words])

    def _check_correct_number_of_lines_in_revisions(
            self, lines, expected_number_of_lines):
        for key in lines.keys():
            self.assertEqual(len(lines[key]), expected_number_of_lines)

    def _check_correct_line_types(self, lines, types):

        for revision in ['revision_1', 'revision_2']:

            for index, line in enumerate(lines[revision]):

                self.assertEqual(
                    StringDiffTool._get_line_type(lines[revision][index]),
                    types[revision][index]
                )

    def _check_correct_line_contents(self, lines, contents):

        for revision in ['revision_1', 'revision_2']:

            for index, line in enumerate(lines[revision]):

                self.assertEqual(
                    self._get_original_line_from_revision(
                        lines[revision][index]),
                    contents[revision][index]
                )

    def _test_correct_number_of_lines(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two\nline three"""

        self._check_correct_number_of_lines_in_revisions(
            self._get_diff_tool(
                revision_1, revision_2, if_unchanged=True).lines,
            3
        )

        # first line is ignored because it is unchanged
        self._check_correct_number_of_lines_in_revisions(
            self._get_diff_tool(
                revision_1, revision_2, if_unchanged=False).lines,
            2
        )

        revision_1 = """line one\nline two\n\nline_four\nline five"""
        revision_2 = """line one\nline two\nline three"""

        # all lines should be accounted for
        self._check_correct_number_of_lines_in_revisions(
            self._get_diff_tool(
                revision_1, revision_2, if_unchanged=True).lines,
            5
        )

        # first and second lines are ignored because they are unchanged
        self._check_correct_number_of_lines_in_revisions(
            self._get_diff_tool(
                revision_1, revision_2, if_unchanged=False).lines,
            3
        )

    def _test_instance_has_correct_properties_for_added_line(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two"""
        diff = StringDiffTool(revision_1, revision_2, if_unchanged=True)

        lines = diff.lines
        self._check_correct_number_of_lines_in_revisions(lines, 2)

        types = {
            'revision_1': ['unchanged', 'empty'],
            'revision_2': ['unchanged', 'addition']
        }
        self._check_correct_line_types(lines, types)

        contents = {
            'revision_1': ['line one', ''],
            'revision_2': ['line one', 'line two']
        }
        self._check_correct_line_contents(lines, contents)

    def _test_instance_has_correct_properties_for_removed_line(self):
        revision_1 = """line one\nline two"""
        revision_2 = """line one"""
        diff = StringDiffTool(revision_1, revision_2, if_unchanged=True)

        lines = diff.lines
        self._check_correct_number_of_lines_in_revisions(lines, 2)

        types = {
            'revision_1': ['unchanged', 'removal'],
            'revision_2': ['unchanged', 'empty']
        }
        self._check_correct_line_types(lines, types)

        contents = {
            'revision_1': ['line one', 'line two'],
            'revision_2': ['line one', '']
        }
        self._check_correct_line_contents(lines, contents)

    def _test_instance_has_correct_properties_for_edited_line(self):
        revision_1 = """line number one has changed"""
        revision_2 = """line one has actually changed"""
        diff = StringDiffTool(revision_1, revision_2)

        lines = diff.lines
        for key in lines.keys():
            self.assertEqual(len(lines[key]), 1)

        types = {
            'revision_1': ['removal'],
            'revision_2': ['addition']
        }
        self._check_correct_line_types(lines, types)

        contents = {
            'revision_1': ['line number one has changed'],
            'revision_2': ['line one has actually changed']
        }
        self._check_correct_line_contents(lines, contents)

    def _test_rendered_lines_work_for_added_line(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two"""
        diff = StringDiffTool(revision_1, revision_2)

        self.assertEqual(
            diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-empty'>1</td>"
                u"<td class='line-content empty'></td>"
            )
        )
        self.assertEqual(
            diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-addition'>1</td>"
                u"<td class='line-content addition'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )

    def _test_rendered_lines_work_for_removed_line(self):
        revision_1 = """line one\nline two"""
        revision_2 = """line one"""
        diff = StringDiffTool(revision_1, revision_2)
        self.assertEqual(
            diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-removal'>1</td>"
                u"<td class='line-content removal'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )
        self.assertEqual(
            diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-empty'>1</td>"
                u"<td class='line-content empty'></td>"
            )
        )

    def _test_rendered_lines_work_for_edited_line(self):
        revision_1 = """line number one has changed"""
        revision_2 = """line one has actually changed"""
        diff = StringDiffTool(revision_1, revision_2)
        self.assertEqual(
            diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-removal'>1</td>"
                u"<td class='line-content removal'>"
                u"line <strong>number</strong> one has changed"
                u"</td>"
            )
        )
        self.assertEqual(
            diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-addition'>1</td>"
                u"<td class='line-content addition'>"
                u"line one has <strong>actually</strong> changed"
                u"</td>"
            )
        )


class TestStringDiffTool(TestBaseDiffTool, unittest.TestCase):

    def _get_diff_tool(self, revision_1, revision_2, if_unchanged):
        return StringDiffTool(revision_1, revision_2, if_unchanged)

    def test_wrong_input_parameters_raises_value_error(self):
        StringDiffTool('', '')

        param_list = [
            ('', ['not a string']),
            (['not a string'], ['not a string']),
            ('', None),
            ('', 0),
            ('', False)
        ]

        for params in param_list:
            with self.assertRaises(ValueError):
                StringDiffTool(params[0], params[1])
            with self.assertRaises(ValueError):
                StringDiffTool(params[1], params[0])

    def test_all_tests(self):
        for attr in dir(TestBaseDiffTool):
            if attr.startswith('_test') and callable(getattr(self, attr)):
                getattr(self, attr)()


class TestListDiffTool(TestBaseDiffTool, unittest.TestCase):

    def _get_diff_tool(self, revision_1, revision_2, if_unchanged):
        return ListDiffTool(
            revision_1.splitlines(), revision_2.splitlines(), if_unchanged)

    def test_wrong_input_parameters_raises_value_error(self):
        ListDiffTool([], [])

        param_list = [
            ([], 'not a list'),
            ('not a string', 'not a string'),
            ([], None),
            ([], 0),
            ([], False)
        ]

        for params in param_list:
            with self.assertRaises(ValueError):
                ListDiffTool(params[0], params[1])
            with self.assertRaises(ValueError):
                ListDiffTool(params[1], params[0])

    def test_all_tests(self):
        for attr in dir(TestBaseDiffTool):
            if attr.startswith('_test') and callable(getattr(self, attr)):
                getattr(self, attr)()
