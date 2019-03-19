import os
import json


def load_countries():
    # Load countries from govuk-country-and-territory-autocomplete frontend package
    helpers_path = os.path.abspath(os.path.dirname(__file__))
    country_file = os.path.join(helpers_path, '../../static/location-autocomplete-canonical-list.json')
    with open(country_file) as f:
        return json.load(f)


COUNTRY_TUPLE = load_countries()
