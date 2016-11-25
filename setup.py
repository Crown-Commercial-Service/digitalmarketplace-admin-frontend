"""
Common utils for Digital Marketplace apps.
"""

from setuptools import setup, find_packages

setup(
    name='dto-digitalmarketplace-admin-frontend',
    version='528',
    url='https://github.com/ausdto/dto-digitalmarketplace-admin-frontend',
    license='MIT',
    author='GDS Developers',
    description='Admin frontend',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'dto-digitalmarketplace-utils',
        'dto-digitalmarketplace-content-loader',
        'dto-digitalmarketplace-apiclient',
        'Flask',
        'Flask-Login',
        'Flask-Bootstrap',
        'pbkdf2',
        'python-dateutil',
        'six',
        'werkzeug',
        'unicodecsv',
        'boto'
    ]
)
