import os

from billy.utils.generic import get_git_rev

here = os.path.abspath(os.path.dirname(__file__))

VERSION = '0.0.0'
version_path = os.path.join(here, 'version.txt')
if os.path.exists(version_path):
    with open(version_path, 'rt') as verfile:
        VERSION = verfile.read().strip()

REVISION = None
revision_path = os.path.join(here, 'revision.txt')
if os.path.exists(revision_path):
    with open(revision_path, 'rt') as rerfile:
        REVISION = rerfile.read().strip()
# cannot find revision from file, try to get it from .git folder
if REVISION is None:
    REVISION = get_git_rev()
