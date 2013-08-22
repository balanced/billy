import os

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.md')).read()
requires = open(os.path.join(here, 'requirements.txt')).read()
requires = map(lambda r: r.strip(), requires.splitlines())


setup(
    name='billy',
    version='0.0.1',
    description='Recurring payment system',
    long_description=readme,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Flask",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Balanced Payment',
    author_email='support@balancedpayments.com',
    url='https://github.com/balanced/billy',
    keywords='billy payment recurring schedule',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    tests_require=[
        'nose-cov',
        'webtest',
        'freezegun',
        'flexmock',
    ],
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = billy:main
    [console_scripts]
    initialize_billy_db = billy.scripts.initializedb:main
    """,
)
