import os

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.md')).read()
requires = open(os.path.join(here, 'requirements.txt')).read()
requires = map(lambda r: r.strip(), requires.splitlines())
test_requires = open(os.path.join(here, 'test-requirements.txt')).read()
test_requires = map(lambda r: r.strip(), test_requires.splitlines())

version = '0.0.0'
version_path = os.path.join(here, 'billy', 'version.txt')
if os.path.exists(version_path):
    version = open(version_path, 'rt').read().strip()

setup(
    name='billy',
    version=version,
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
    install_requires=requires,
    tests_require=test_requires,
    entry_points="""\
    [paste.app_factory]
    main = billy:main
    [console_scripts]
    initialize_billy_db = billy.scripts.initializedb:main
    process_billy_tx = billy.scripts.process_transactions:main
    """,
)
