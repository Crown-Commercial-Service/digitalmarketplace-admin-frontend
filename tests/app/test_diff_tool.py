from collections import OrderedDict
from itertools import chain

import pytest
from lxml import html

from app import content_loader
from app.main.helpers.diff_tools import html_diff_tables_from_sections_iter
from .helpers import BaseApplicationTest


class TestHtmlDiffTablesFromSections(BaseApplicationTest):
    _expected_removal_content_column = 1
    _expected_addition_content_column = 3

    @pytest.mark.parametrize("framework_slug,lot_slug,service_data_a,service_data_b,expected_rem_qs,expected_add_qs", (
        (
            # framework_slug
            "g-cloud-9",
            # lot_slug
            "cloud-software",
            # service_data_a
            {
                "serviceName": "Metempsychosis",
                "serviceDescription": "Only born male transubstantial heir of Rudolf Virag.",
            },
            # service_data_b
            {
                "serviceName": "Metempsychosis",
                "serviceDescription": "Only born male transubstantial heir of Rudolf Bloom.",
            },
            # expected_rem_qs (question ids expected to create diffs with "added" fragments)
            ("serviceDescription",),
            # expected_rem_qs (question ids expected to create diffs with "removed" fragments)
            ("serviceDescription",),
        ),
        (
            "g-cloud-9",
            "cloud-support",
            {
                "serviceName": "Ellen Higgins, second daughter of Julius Karoly",
                "serviceDescription": "Fanny Hegarty\nRichard Goulding\n\nChristina Grier\n",
            },
            {
                "serviceName": "Ellen Higgins, second daughter of Julius Higgins",
                "serviceDescription": "Fanny Higgins\n\nSimon Dedalus of Cork\nRichard Goulding\n\nChristina Grier\n",
            },
            ("serviceName", "serviceDescription",),
            ("serviceName", "serviceDescription",),
        ),
        (
            "g-cloud-8",
            "iaas",
            {
                "serviceName": u"GENTLEMEN\u2751OF\u2751THE\u2751PRESS",
                "serviceSummary": "Grossbooted draymen rolled barrels dullthudding out of Prince's\n" +
                                  "stores and bumped them up on the brewery float. On the brewery float bumped\n" +
                                  "dullthudding barrels rolled by grossbooted draymen out of Prince's stores.",
            },
            {
                "serviceName": u"GENTLEMEN \u2751 OF \u2751 THE \u2751 PRESS",
                "serviceSummary": "Grossbooted draymen rolled barrels dullthudding out of Prince's\n" +
                                  "stores and bumped them up on the brewery float. On the brewery float bumped\n" +
                                  "dullthudding barrels rolled by grossbooted draymen out of Prince's stores.",
            },
            (),
            ("serviceName",),
        ),
        (
            "g-cloud-9",
            "cloud-hosting",
            {
                "serviceName": "Infinitely preceding deletion",
                "serviceDescription": "To reflect that each <del> who enters imagines himself to be the first to\n" +
                                      "</del> whereas he <ins> always the last term of a preceding series",
                "serviceFeaturesHostingAndSoftware": [
                    "Burke",
                    "Joseph Cuffe",
                    "Wisdom Hely",
                    "Alderman John Hooper",
                    "Dr Francis Brady",
                ],
                "somethingIrrelevant": "decomposed vegetable missiles",
            },
            {
                "serviceName": "Infinitely preceding deletion",
                "serviceDescription": "He is neither first <ins> nor </ins> <del> nor only nor alone in a series\n" +
                                      "originating in & repeated to </del>.",
                "serviceFeaturesHostingAndSoftware": [
                    "Burke",
                    "Joseph Cuffe",
                    "Wisdom Hely",
                    "Alderman John Hooper",
                    "Dr. Francis Brady",
                    "Father Sebastian of Mount Argus",
                    "A bootblack at the General Post Office",
                ],
            },
            ("serviceDescription",),
            ("serviceDescription", "serviceFeaturesHostingAndSoftware",),
        ),
        (
            "g-cloud-9",
            "cloud-support",
            {
                "serviceName": "An unsatisfactory equation",
                "serviceDescription": "An exodus and return\n in time\n  through reversible space",
                "serviceBenefitsSupport": [
                    "The lateness of the hour,    rendering procrastinatory   ",
                    "The obscurity of the night, rendering invisible",
                    "The uncertainty of thoroughfares, rendering perilous",
                    "The necessity for repose, obviating movement",
                    "The proximity of an occupied bed, obviating research",
                    "The anticipation of warmth (human) tempered with coolness (linen)",
                    "The statue of Narcissus, sound without echo, desired desire",
                ],
            },
            {
                "serviceName": "An unsatisfactory equation",
                "serviceDescription": "\nAn exodus and return\n in space\n through irreversible time",
                "serviceBenefitsSupport": [
                    "The anticipation of warmth (human) tempered with coolness (linen)",
                    "The lateness of the hour,    rendering procrastinatory   ",
                    "The necessity for repose, obviating movement",
                    "The obscurity of the night, rendering invisible",
                    "The proximity of an occupied bed, obviating research",
                    "The statue of Narcissus, sound without echo, desired desire",
                    "The uncertainty of thoroughfares, rendering perilous",
                ],
                "serviceFeaturesSupport": [
                    "The removal of nocturnal solitude",
                ],
            },
            ("serviceDescription", "serviceBenefitsSupport",),
            ("serviceDescription", "serviceBenefitsSupport", "serviceFeaturesSupport",),
        ),
    ))
    @pytest.mark.parametrize("table_preamble_template", (None, "diff_table/_table_preamble.html",))
    def test_common_properties(
        self,
        framework_slug,
        lot_slug,
        service_data_a,
        service_data_b,
        expected_rem_qs,
        expected_add_qs,
        table_preamble_template,
    ):
        # because there is no single canonical "correct" representation of a diff between two documents, we can't just
        # test the output verbatim as it would be a fragile test. instead we can test for a bunch of properties that
        # must always be true of an output we would consider valid

        service_data_a, service_data_b = (dict(s, lot=lot_slug) for s in (service_data_a, service_data_b,))
        content_sections = content_loader.get_manifest(
            framework_slug,
            'edit_service_as_admin',
        ).filter(service_data_b).sections

        with self.app.app_context():
            diffs = OrderedDict((q_id, html_diff) for sec_slug, q_id, html_diff in html_diff_tables_from_sections_iter(
                content_sections,
                service_data_a,
                service_data_b,
                table_preamble_template=table_preamble_template,
            ))

        for question_id, html_diff in diffs.items():
            table_element = html.fragment_fromstring(html_diff)

            # these should all have been removed
            assert not table_element.xpath(".//a")
            assert not table_element.xpath(".//colgroup")
            assert not table_element.xpath(".//*[@id]")

            # there should be a non-empty caption tag if and only if table_preamble_template is supplied
            if table_preamble_template is None:
                assert not table_element.xpath(".//caption")
            else:
                assert table_element.xpath("./caption[normalize-space(string())]")

            # all td.line-content.removal elements should appear in the same (expected) column
            for tr in table_element.xpath(
                "./tbody/tr[./td[contains(@class, 'line-content')][contains(@class, 'removal')]]"
            ):
                assert len(tr.xpath("./td[contains(@class, 'line-content')][contains(@class, 'removal')]")) == 1
                assert len(tr.xpath(
                    "./td[contains(@class, 'line-content')][contains(@class, 'removal')]/preceding-sibling::*"
                )) == self._expected_removal_content_column
            # all td.line-content.addition elements should appear in the same (expected) column
            for tr in table_element.xpath(
                "./tbody/tr[./td[contains(@class, 'line-content')][contains(@class, 'addition')]]"
            ):
                assert len(tr.xpath("./td[contains(@class, 'line-content')][contains(@class, 'addition')]")) == 1
                assert len(tr.xpath(
                    "./td[contains(@class, 'line-content')][contains(@class, 'addition')]/preceding-sibling::*"
                )) == self._expected_addition_content_column

            # the only del elements should appear in td.line-content.removal elements
            assert len(table_element.xpath(".//del")) == len(
                table_element.xpath(
                    "./tbody/tr/td[contains(@class, 'line-content')][contains(@class, 'removal')]/del"
                )
            )
            # and there shouldn't be any td.line-content.removal elements that don't have at least one del element
            assert not table_element.xpath(
                ".//td[contains(@class, 'line-content')][contains(@class, 'removal')][not(.//del)]"
            )

            # the only ins elements should appear in td.line-content.addition elements
            assert len(table_element.xpath(".//ins")) == len(
                table_element.xpath(
                    "./tbody/tr/td[contains(@class, 'line-content')][contains(@class, 'addition')]/ins"
                )
            )
            # and there shouldn't be any td.line-content.addition elements that don't have at least one ins element
            assert not table_element.xpath(
                ".//td[contains(@class, 'line-content')][contains(@class, 'addition')][not(.//ins)]"
            )

            # content should have been purged of all nbsps
            assert not table_element.xpath(
                ".//td[contains(@class, 'line-content')][contains(string(), $nbsp)]",
                nbsp=u"\u00a0",
            )

            # yes, this is awfully familiar code from the innards of html_diff_tables_from_sections_iter so there's a
            # degree to which we're marking our own homework with this, but it's a little difficult to see an
            # alternative
            expected_content_a, expected_content_b = (
                [
                    (line or " ")  # diff outputs an extraneous space in some blank line cases, which is ok by us
                    for line in (q.splitlines() if isinstance(q, str) else q)
                ]
                for q in (r.get(question_id, []) for r in (service_data_a, service_data_b,))
            )
            # assert some things about the content in each line-content column
            for expected_content, expected_content_column in (
                (expected_content_a, self._expected_removal_content_column,),
                (expected_content_b, self._expected_addition_content_column,),
            ):
                # the collapsed string content of the collection of tds from the expected column which have a non-empty
                # line-number td directly preceding them should equal the expected content. note here we're not giving
                # any leeway for extra whitespace because the intention is to be able to display this with whitespace-
                # preserving css. but that could always be relaxed if totally necessary. also note if there were nbsps
                # in our data this would not work because they are purged unconditionally.
                assert [
                    (elem.xpath("string()") or " ")  # normalizing blank lines to single spaces, reason mentioned above
                    for elem in table_element.xpath(
                        "./tbody/tr/td[$i][contains(@class, 'line-content')]"
                        "[normalize-space(string(./preceding-sibling::td[1][contains(@class, 'line-number')]))]",
                        # xpath's element indexing is 1-based
                        i=expected_content_column + 1,
                    )
                ] == expected_content

            # assert some things about each row
            for tr in table_element.xpath("./tbody/tr"):
                # note here how xpath's element indexing is 1-based
                content_remside = tr.xpath("string(./td[$i])", i=self._expected_removal_content_column + 1)
                content_addside = tr.xpath("string(./td[$i])", i=self._expected_addition_content_column + 1)

                # in lines where we have additions/removals,,,
                if tr.xpath(
                    "./td[contains(@class, 'line-content')]" +
                    "[contains(@class, 'addition') or contains(@class, 'removal')]"
                ):
                    # row should have content on at least one side
                    assert content_addside or content_remside

                    # if no content on one side, all content on other side should be in a del/ins
                    if not content_remside:
                        assert content_addside == tr.xpath(
                            "string(./td[contains(@class, 'line-content')][contains(@class, 'addition')]/ins)"
                        )
                    if not content_addside:
                        assert content_remside == tr.xpath(
                            "string(./td[contains(@class, 'line-content')][contains(@class, 'removal')]/del)"
                        )

                    # line number should be on a side if and only if there is content on that side
                    assert bool(tr.xpath(
                        "string(./td[contains(@class, 'line-content')][contains(@class, 'removal')])"
                    )) == bool(tr.xpath(
                        "normalize-space(string(./td[contains(@class, 'line-number')]" +
                        "[contains(@class, 'line-number-removal')]))"
                    ))
                    assert bool(tr.xpath(
                        "string(./td[contains(@class, 'line-content')][contains(@class, 'addition')])"
                    )) == bool(tr.xpath(
                        "normalize-space(string(./td[contains(@class, 'line-number')]" +
                        "[contains(@class, 'line-number-add')]))"
                    ))

                    # line-content tds which are empty should have line-non-existent class
                    assert all(
                        bool("line-non-existent" in td.attrib.get("class", "")) == (not td.xpath("string()"))
                        for td in tr.xpath("./td[contains(@class, 'line-content')]")
                    )
                else:  # but if there aren't any additions/removals...
                    # the content should be equal on both sides
                    assert content_remside == content_addside

                    # there shouldn't be any line-non-existent tds
                    assert not tr.xpath("./td[contains(@class, 'line-non-existent')]")

        for question in chain.from_iterable(section.questions for section in content_sections):
            # check a question we expect to have removals does and ones we expect not to ...doesn't.
            assert bool((question_id in diffs) and html.fragment_fromstring(diffs[question_id]).xpath(
                "./tbody/tr/td[contains(@class, 'line-content')][contains(@class, 'removal')]"
            )) == (question_id in expected_rem_qs)
            # check a question we expect to have additions does and ones we expect not to ...doesn't.
            assert bool((question_id in diffs) and html.fragment_fromstring(diffs[question_id]).xpath(
                "./tbody/tr/td[contains(@class, 'line-content')][contains(@class, 'addition')]"
            )) == (question_id in expected_add_qs)
            # check a question we expect to have neither additions or removals to not be present in diffs at all
            assert (question_id in diffs) == (question_id in expected_rem_qs or question_id in expected_add_qs)

    def test_identical_data(self):
        # these two should be identical in as far as the data we're concerned about
        service_data_a = {
            "lot": "cloud-support",
            "serviceName": "On the range",
            "serviceFeaturesSupport": [
                "A blue enamelled saucepan",
                "A black iron kettle",
            ],
            "irrelevantThing": "Five coiled spring housebells",
        }
        service_data_b = {
            "lot": "cloud-support",
            "serviceName": "On the range",
            "serviceFeaturesSupport": [
                "A blue enamelled saucepan",
                "A black iron kettle",
            ],
            "irrelevantThing": "Six coiled spring housebells",
            "anotherIrrelevancy": "A curvilinear rope",
        }

        content_sections = content_loader.get_manifest(
            "g-cloud-9",
            'edit_service_as_admin',
        ).filter(service_data_b).sections

        assert not tuple(html_diff_tables_from_sections_iter(content_sections, service_data_a, service_data_b))
