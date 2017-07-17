import difflib
from itertools import chain

from flask import Markup, render_template
from flask._compat import string_types

from lxml import html

from dmcontent.questions import Multiquestion


def _question_iter(question):
    # type testing is weird - this should eventually belong in the question subclass itself
    if isinstance(question, Multiquestion):
        for sub_question in question.questions:
            yield sub_question
    else:
        yield question


def html_diff_tables_from_sections_iter(
        sections,
        revision_1,
        revision_2,
        table_preamble_template=None,
):
    html_diff = difflib.HtmlDiff()

    for section in sections:
        for question in chain.from_iterable(_question_iter(question) for question in section['questions']):
            q1, q2 = (r.get(question['id'], []) for r in (revision_1, revision_2,))
            if q1 != q2:
                q1, q2 = (_get_value_for_difflib(q) for q in (q1, q2,))
                yield section.slug, question.id, Markup(_clean_difflib_html_table(
                    html_diff.make_table(q1, q2),
                    table_preamble_template=table_preamble_template,
                    table_preamble_context={
                        "section": section,
                        "question": question,
                    },
                ))


def _get_value_for_difflib(thing):
    if isinstance(thing, string_types):
        return thing.splitlines()
    elif isinstance(thing, bool):
        return ["{}".format(thing)]
    else:
        return thing


def _strip_nbsp(content):
    return content.replace(u"\u00a0", u" ")


def _strip_element_nbsp(element):
    element.text = element.text and _strip_nbsp(element.text)
    element.tail = element.tail and _strip_nbsp(element.tail)
    for child_element in element:
        _strip_element_nbsp(child_element)


def _clean_difflib_html_table(table_src, table_preamble_template=None, table_preamble_context={}):
    # difflib doesn't produce html *quite* how we would like, so we do the admittedly slightly strange thing here of
    # parsing it, modifying the result in-place and re-serializing it for rendering. this is, in my opinion, the least-
    # worst thing to do, because it allows us to take advantage of the (well tested) logic of difflib.HtmlDiff while
    # just adding relatively simple style-mangling code of our own.
    #
    # another (perhaps more obvious) alternative to this would have been to adapt our stytles to difflib's output,
    # but... frankly our style scheme for this is more well thought out and, more importantly, already cross-browser
    # tested.
    table_element = html.fragment_fromstring(table_src)

    # colgroups not wanted
    for colgroup in table_element.xpath(".//colgroup"):
        colgroup.getparent().remove(colgroup)

    # column of links not wanted
    for diff_next in table_element.xpath(".//td[@class='diff_next']"):
        diff_next.getparent().remove(diff_next)

    # this isn't even valid html5 anymore
    for td_nowrap in table_element.xpath(".//td[@nowrap]"):
        del td_nowrap.attrib["nowrap"]

    for key in table_element.keys():
        del table_element.attrib[key]

    # we can't really safely use ids (who knows if we're going to use >1 of these in a page?)
    for element in table_element.xpath(".//*[@id]"):
        del element.attrib["id"]

    # difflib very helpfully replaces all our spaces with nbsp, which is not something we want
    _strip_element_nbsp(table_element.xpath("./tbody")[0])

    for line_number_td in table_element.xpath(".//td[@class='diff_header']"):
        line_number_td.attrib["class"] = "line-number"

    for tr in table_element.xpath("./tbody/tr"):
        tr[0].attrib["class"] = tr[2].attrib["class"] = "line-number"
        tr[1].attrib["class"] = tr[3].attrib["class"] = "line-content"

        if (tr[0].text or "").strip() or len(tr[0]):  # i.e. left side has what is presumably a line number
            if len(tr[1]):  # i.e. left side is interesting because the content has (presumably span.diff_*) child elems
                tr[0].attrib["class"] += " line-number-removal"
                tr[1].attrib["class"] += " removal"
                for span in tr[1].xpath("./span[@class='diff_sub' or @class='diff_chg']"):
                    span.tag = "del"
                    del span.attrib["class"]
        else:
            tr[0].attrib["class"] += " line-non-existent"
            tr[1].attrib["class"] += " line-non-existent"

        if (tr[2].text or "").strip() or len(tr[2]):  # i.e. right side has what is presumably a line number
            if len(tr[3]):  # i.e. right side's interesting because the content has (presumably span.diff_*) child elems
                tr[2].attrib["class"] += " line-number-addition"
                tr[3].attrib["class"] += " addition"
                for span in tr[3].xpath("./span[@class='diff_add' or @class='diff_chg']"):
                    span.tag = "ins"
                    del span.attrib["class"]
        else:
            tr[2].attrib["class"] += " line-non-existent"
            tr[3].attrib["class"] += " line-non-existent"

    if table_preamble_template:
        preamble_src = render_template(table_preamble_template, **table_preamble_context)
        preamble_elements = html.fragments_fromstring(preamble_src)
        for element in reversed(preamble_elements):
            table_element.insert(0, element)

    return html.tostring(table_element, encoding="unicode")
