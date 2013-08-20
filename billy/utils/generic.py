from __future__ import unicode_literals

import os
import uuid
import decimal

B58_CHARS = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
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
    return b''.join(reversed(result))


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
    """Round down money value to cent (truncate to), for example, $5.66666
    will be rounded to $5.66

    :param amount: the money amount to be rounded
    :return: the rounded money amount
    """
    return amount.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
