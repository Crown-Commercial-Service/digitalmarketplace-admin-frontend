DEPRECATED_FRAMEWORK_SLUGS = ['g-cloud-4', 'g-cloud-5', 'g-cloud-6']


def company_details_from_supplier(supplier):
    address = {"country": supplier.get("registrationCountry")}
    if len(supplier.get('contactInformation', [])) > 0:
        address.update({
            "street_address_line_1": supplier['contactInformation'][0].get('address1'),
            "locality": supplier["contactInformation"][0].get("city"),
            "postcode": supplier["contactInformation"][0].get("address1"),
        })
    return {
        "duns_number": supplier.get("dunsNumber"),
        "registration_number": (
            supplier.get("companiesHouseNumber")
            or
            supplier.get("otherCompanyRegistrationNumber")
        ),
        "registered_name": supplier.get("registeredName"),
        "address": address
    }


def company_details_from_supplier_framework_declaration(declaration):
    return {
        "duns_number": declaration.get("supplierDunsNumber"),
        "registration_number": declaration.get("supplierCompanyRegistrationNumber"),
        "trading_name": declaration.get("supplierTradingName"),
        "registered_name": declaration.get("supplierRegisteredName"),
        "address": {
            "street_address_line_1": declaration.get("supplierRegisteredBuilding"),
            "locality": declaration.get("supplierRegisteredTown"),
            "postcode": declaration.get("supplierRegisteredPostcode"),
            "country": declaration.get("supplierRegisteredCountry"),
        },
    }


def interesting_frameworks(supplier_framework_interests, current_user, frameworks):
    """
    :param supplier_framework_interests: SupplierFramework objects for the supplier
    :param current_user: flask user (should be an admin)
    :param frameworks: list of all framework objects
    :return: List of frameworks of interest to a particular admin role, sorted by oldest first
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

    interesting_supplier_frameworks = []
    for supplier_framework in supplier_framework_interests:
        if framework_info.get(supplier_framework["frameworkSlug"], {}).get("status") in useful_statuses:
            # Save the framework name to the SupplierFramework for use in template
            supplier_framework['frameworkName'] = framework_info.get(supplier_framework["frameworkSlug"], {})['name']
            interesting_supplier_frameworks.append(supplier_framework)

    return sorted(
        interesting_supplier_frameworks,
        key=lambda sf: framework_info[sf["frameworkSlug"]]['frameworkLiveAtUTC']
    )


def get_company_details_and_most_recent_interest(supplier_frameworks, supplier):
    # Get the company details and the declaration they were taken from (if any)
    if supplier_frameworks:
        most_recent_framework_interest = supplier_frameworks[-1]
    else:
        most_recent_framework_interest = {}

    if most_recent_framework_interest.get("declaration"):
        company_details = company_details_from_supplier_framework_declaration(
            most_recent_framework_interest["declaration"]
        )
    else:
        company_details = company_details_from_supplier(supplier)

    return company_details, most_recent_framework_interest
