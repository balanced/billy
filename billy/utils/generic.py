from __future__ import unicode_literals
import os
import uuid
import json
import datetime

import pytz

B58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58_BASE = len(B58_CHARS)


def b58encode(s):
    """Do a base 58 encoding (alike base 64, but in 58 char only)

    From https://bitcointalk.org/index.php?topic=1026.0

    by Gavin Andresen (public domain)

    """
    value = 0
    for i, c in enumerate(reversed(s)):
        value += ord(c) * (256 ** i)

    result = []
    while value >= B58_BASE:
        div, mod = divmod(value, B58_BASE)
        c = B58_CHARS[mod]
        result.append(c)
        value = div
    result.append(B58_CHARS[value])
    return ''.join(reversed(result))


def make_guid():
    """Generate a GUID and return in base58 encoded form

    """
    uid = uuid.uuid1().bytes
    return b58encode(uid)


def make_api_key(size=32):
    """Generate a random API key, should be as random as possible
    (not predictable)

    :param size: the size in byte to generate
        note that it will be encoded in base58 manner,
        the length will be longer than the aksed size
    """
    # TODO: os.urandom collect entropy from devices in linux,
    # it might block when there is no enough entropy
    # attacker might use this to perform a DOS attack
    # maybe we can use another way to avoid such situation
    # however, this is good enough currently
    random = os.urandom(size)
    return b58encode(random)


def round_down_cent(amount):
    """Round down money value in cent (drop float points), for example, 5.66666
    cents will be rounded to 5 cents

    :param amount: the money amount in cent to be rounded
    :return: the rounded money amount
    """
    return int(amount)


def get_git_rev(project_dir=None):
    """Get current GIT reversion if it is available, otherwise, None is
    returned

    """
    if project_dir is None:
        import billy
        pkg_dir = os.path.dirname(billy.__file__)
        project_dir, _ = os.path.split(pkg_dir)
    git_dir = os.path.join(project_dir, '.git')
    head_file = os.path.join(git_dir, 'HEAD')
    try:
        with open(head_file, 'rt') as f:
            content = f.read().strip()
        if content.startswith('ref: '):
            ref_file = os.path.join(git_dir, content[5:])
            with open(ref_file, 'rt') as f:
                rev = f.read().strip()
            return rev
    except IOError:
        return None
    return content


def utc_now():
    """Like datetime.datetime.utcnow(), but the datetime.tzinfo will be
    pytz.utc

    """
    return datetime.datetime.now(pytz.utc)


def utc_datetime(*args, **kwargs):
    """Create a datetime with pytz.utc tzinfo

    """
    return datetime.datetime(*args, tzinfo=pytz.utc, **kwargs)


def dumps_pretty_json(obj):
    """Dump prettified json into string

    """
    return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
