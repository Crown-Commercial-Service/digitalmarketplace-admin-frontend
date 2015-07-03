import unittest
from app.main.helpers.diff_tools import StringDiffTool
from flask import Markup


class TestDiffTool(unittest.TestCase):

    maxDiff = None

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

    def test_correct_number_of_lines(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two\nline three"""

        self._check_correct_number_of_lines_in_revisions(
            StringDiffTool(revision_1, revision_2, if_unchanged=True).lines,
            3
        )

        self._check_correct_number_of_lines_in_revisions(
            StringDiffTool(revision_1, revision_2, if_unchanged=False).lines,
            2
        )

        revision_1 = """line one\nline two\n\nline_four\nline five"""
        revision_2 = """line one\nline two\nline three"""

        # all lines should be accounted for
        self._check_correct_number_of_lines_in_revisions(
            StringDiffTool(revision_1, revision_2, if_unchanged=True).lines,
            5
        )

        # lines 1 and 2 are unchanged, so they won't be here
        self._check_correct_number_of_lines_in_revisions(
            StringDiffTool(revision_1, revision_2, if_unchanged=False).lines,
            3
        )

    def test_instance_has_correct_properties_for_added_line(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two"""
        string_diff = StringDiffTool(revision_1, revision_2, if_unchanged=True)

        lines = string_diff.lines
        self._check_correct_number_of_lines_in_revisions(lines, 2)

        # first line in each revision is "line one", which is the same
        self.assertFalse(string_diff.has_changes(lines['revision_1'][0]))
        self.assertFalse(string_diff.has_changes(lines['revision_2'][0]))

        # revision_2 should register changes
        self.assertFalse(string_diff.has_changes(lines['revision_1'][1]))
        self.assertTrue(string_diff.has_changes(lines['revision_2'][1]))

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_1'][1]),
            '')

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_2'][1]),
            'line two')

    def test_instance_has_correct_properties_for_removed_line(self):
        revision_1 = """line one\nline two"""
        revision_2 = """line one"""
        string_diff = StringDiffTool(revision_1, revision_2, if_unchanged=True)

        lines = string_diff.lines
        self._check_correct_number_of_lines_in_revisions(lines, 2)

        # first line in each revision is "line one", which is the same
        self.assertFalse(string_diff.has_changes(lines['revision_1'][0]))
        self.assertFalse(string_diff.has_changes(lines['revision_2'][0]))

        # revision_1 should register changes
        self.assertTrue(string_diff.has_changes(lines['revision_1'][1]))
        self.assertFalse(string_diff.has_changes(lines['revision_2'][1]))

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_1'][1]),
            'line two')

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_2'][1]),
            '')

    def test_instance_has_correct_properties_for_edited_line(self):
        revision_1 = """line number one has changed"""
        revision_2 = """line one has actually changed"""
        string_diff = StringDiffTool(revision_1, revision_2)

        lines = string_diff.lines
        for key in lines.keys():
            self.assertEqual(len(lines[key]), 1)

        self.assertTrue(string_diff.has_changes(lines['revision_1'][0]))
        self.assertTrue(string_diff.has_changes(lines['revision_2'][0]))

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_1'][0]),
            'line number one has changed')

        self.assertEqual(
            self._get_original_line_from_revision(lines['revision_2'][0]),
            'line one has actually changed')

    def test_rendered_lines_work_for_added_line(self):
        revision_1 = """line one"""
        revision_2 = """line one\nline two"""
        string_diff = StringDiffTool(revision_1, revision_2)

        self.assertEqual(
            string_diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='number line-number unchanged'>1</td>"
                u"<td class='unchanged'></td>"
            )
        )
        self.assertEqual(
            string_diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='number line-number addition'>1</td>"
                u"<td class='addition'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )

    def test_rendered_lines_work_for_removed_line(self):
        revision_1 = """line one\nline two"""
        revision_2 = """line one"""
        string_diff = StringDiffTool(revision_1, revision_2)
        self.assertEqual(
            string_diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='number line-number removal'>1</td>"
                u"<td class='removal'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )
        self.assertEqual(
            string_diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='number line-number unchanged'>1</td>"
                u"<td class='unchanged'></td>"
            )
        )

    def test_rendered_lines_work_for_edited_line(self):
        revision_1 = """line number one has changed"""
        revision_2 = """line one has actually changed"""
        string_diff = StringDiffTool(revision_1, revision_2)
        self.assertEqual(
            string_diff.render_lines()['revision_1'][0],
            Markup(
                u"<td class='number line-number removal'>1</td>"
                u"<td class='removal'>"
                u"line <strong>number</strong> one has changed"
                u"</td>"
            )
        )
        self.assertEqual(
            string_diff.render_lines()['revision_2'][0],
            Markup(
                u"<td class='number line-number addition'>1</td>"
                u"<td class='addition'>"
                u"line one has <strong>actually</strong> changed"
                u"</td>"
            )
        )
