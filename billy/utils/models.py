import os
import uuid

from sqlalchemy import Enum

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

class Enum(Enum):
    """
    Better sqlalchemy enum with a getattr
    """
    def __getattr__(self, item):
        if item in self.enums:
            return item
        raise ValueError('{} not set.'.format(item))



def b58encode(s):
    """From https://bitcointalk.org/index.php?topic=1026.0

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

