import unittest
from app.main.helpers.diff_tools import render_lines
from flask import Markup


class TestDiffToolsHelpers(unittest.TestCase):

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
        revision_1 = """line one""".splitlines()
        revision_2 = """line one\nline two\nline three""".splitlines()

        self._check_correct_number_of_lines_in_revisions(
            render_lines(
                revision_1,
                revision_2,
                include_unchanged_lines_in_output=True),
            3
        )

        # first line is ignored because it is unchanged
        self._check_correct_number_of_lines_in_revisions(
            render_lines(
                revision_1,
                revision_2,
                include_unchanged_lines_in_output=False),
            2
        )

        revision_1 = """line one\nline two\n\nline_four\nline five""".splitlines()  # noqa
        revision_2 = """line one\nline two\nline three""".splitlines()

        # all lines should be accounted for
        self._check_correct_number_of_lines_in_revisions(
            render_lines(
                revision_1,
                revision_2,
                include_unchanged_lines_in_output=True),
            5
        )

        # first and second lines are ignored because they are unchanged
        self._check_correct_number_of_lines_in_revisions(
            render_lines(
                revision_1,
                revision_2,
                include_unchanged_lines_in_output=False),
            3
        )

    def test_rendered_lines_work_for_added_line(self):
        revision_1 = """line one""".splitlines()
        revision_2 = """line one\nline two""".splitlines()
        rendered_lines = render_lines(revision_1, revision_2)

        self.assertEqual(
            rendered_lines['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-empty'>2</td>"
                u"<td class='line-content empty'></td>"
            )
        )
        self.assertEqual(
            rendered_lines['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-addition'>2</td>"
                u"<td class='line-content addition'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )

    def test_rendered_lines_work_for_removed_line(self):
        revision_1 = """line one\nline two""".splitlines()
        revision_2 = """line one""".splitlines()
        rendered_lines = render_lines(revision_1, revision_2)

        self.assertEqual(
            rendered_lines['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-removal'>2</td>"
                u"<td class='line-content removal'>"
                u"<strong>line two</strong>"
                u"</td>"
            )
        )
        self.assertEqual(
            rendered_lines['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-empty'>2</td>"
                u"<td class='line-content empty'></td>"
            )
        )

    def test_rendered_lines_work_for_edited_line(self):
        revision_1 = """line number one has changed""".splitlines()
        revision_2 = """line one has actually changed""".splitlines()
        rendered_lines = render_lines(revision_1, revision_2)
        self.assertEqual(
            rendered_lines['revision_1'][0],
            Markup(
                u"<td class='line-number line-number-removal'>1</td>"
                u"<td class='line-content removal'>"
                u"line <strong>number</strong> one has changed"
                u"</td>"
            )
        )
        self.assertEqual(
            rendered_lines['revision_2'][0],
            Markup(
                u"<td class='line-number line-number-addition'>1</td>"
                u"<td class='line-content addition'>"
                u"line one has <strong>actually</strong> changed"
                u"</td>"
            )
        )
