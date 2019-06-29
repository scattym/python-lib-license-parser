from setuptools import setup, find_packages

setup(
    name='licenseparser',
    version='1.2',
    description='Library for working with drivers license data',
    url='https://bitbucket.org/poslive/python-lib-license-parser.git',
    author='Matt Clark',
    author_email='mattjclark0407@hotmail.com',
    license='Copyright (C) Matt Clark - All Rights Reserved',
    packages=find_packages(),
    install_requires=[
    ],
    dependency_links=[
    ],
    scripts=[
        'scripts/send_card_data'
    ],
    zip_safe=True
)
