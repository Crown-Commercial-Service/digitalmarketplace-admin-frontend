from urllib.parse import urlparse, parse_qs


def get_nav_args_from_api_response_links(links, prev_next_label, request_args, preserved_kwargs):
    """
    Get prev/next page numbers from object's API response, plus any extra request args for the URL
    :param links: dict of links from the API response, e.g. {'self': ..., 'prev': ... 'next': ...}
    :param prev_next_label: string, either 'prev' or 'next'
    :param request: the request_args MultiDict with any GET args
    :param preserved_kwargs: list of string kwargs that should be kept to build the prev/next URLs
    :return: dict of URL params, or None if there's no prev/next link.

    e.g. for the 'prev' link on page 2 of a supplier name search, we'd want
             {'page': 1, 'supplier_name': 'foo'}

    and on for the 'next' link we'd want {'page': 3, 'supplier_name': 'foo'}.

    If there are no prev/next links in the response then return None - we don't want to build the URL.
    """
    if prev_next_label not in links:
        return None

    page_arg = parse_qs(urlparse(links[prev_next_label]).query)

    navigation_args = {
        'page': page_arg['page'][0] if page_arg else None
    }

    for kwarg in preserved_kwargs:
        if request_args.get(kwarg):
            navigation_args[kwarg] = request_args.get(kwarg)

    return navigation_args
