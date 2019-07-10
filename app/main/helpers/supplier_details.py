DEPRECATED_FRAMEWORK_SLUGS = ['g-cloud-4', 'g-cloud-5', 'g-cloud-6']


def get_company_details_from_supplier(supplier):
    address = {"country": supplier.get("registrationCountry")}
    if len(supplier.get('contactInformation', [])) > 0:
        address.update({
            "street_address_line_1": supplier['contactInformation'][0].get('address1'),
            "locality": supplier["contactInformation"][0].get("city"),
            "postcode": supplier["contactInformation"][0].get("postcode"),
        })
    return {
        "duns_number": supplier.get("dunsNumber"),
        "registration_number": (
            supplier.get("companiesHouseNumber")
            or
            supplier.get("otherCompanyRegistrationNumber")
        ),
        "registered_with": "companies_house" if "companiesHouseNumber" in supplier else "unknown",
        "registered_name": supplier.get("registeredName"),
        "address": address
    }


def get_supplier_frameworks_visible_for_role(supplier_frameworks, current_user, frameworks):
    """
    :param supplier_frameworks: list of SupplierFramework objects for the supplier
    :param current_user: flask user (should be an admin)
    :param frameworks: list of all framework objects
    :return: List of frameworks visible to a particular admin role, sorted by oldest first
    """
    # Build dict of status and frameworkLiveAtUTC info for recent (G7 and up) frameworks
    framework_info = {
        framework['slug']: {
            'status': framework['status'],
            'name': framework['name'],
            'frameworkLiveAtUTC': framework['frameworkLiveAtUTC']
        } for framework in frameworks
        if framework['slug'] not in DEPRECATED_FRAMEWORK_SLUGS
    }

    if current_user.has_role('admin-ccs-sourcing'):
        useful_statuses = ["open", "pending", "standstill", "live", "expired"]
    else:
        useful_statuses = ["live", "expired"]

    visible_supplier_frameworks = []
    for supplier_framework in supplier_frameworks:
        if framework_info.get(supplier_framework["frameworkSlug"], {}).get("status") in useful_statuses:
            # Save the framework name to the SupplierFramework for use in template
            supplier_framework['frameworkName'] = framework_info.get(supplier_framework["frameworkSlug"], {})['name']
            visible_supplier_frameworks.append(supplier_framework)

    return sorted(
        visible_supplier_frameworks,
        key=lambda sf: framework_info[sf["frameworkSlug"]]['frameworkLiveAtUTC']
    )
