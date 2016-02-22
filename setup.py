from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(
    name='ckanext-birmingham',
    version=version,
    description="",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.birmingham'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        up_to_n_editors=ckanext.birmingham.plugin:UpToNEditorsPlugin
        customizable_featured_image=ckanext.birmingham.customizable_featured_image:CustomizableFeaturedImagePlugin
        birmingham=ckanext.birmingham.plugin:BirminghamPlugin

    ''',
)
