import uuid

ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def base62_encode(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if num == 0:
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def uuid_factory(prefix=None):
    """
    Given a prefix, which defaults to None, will generate a function
    which when called, will generate a hex uuid string using uuid.uuid1()

    If a prefix string is passed, it prefixes the uuid.
    """


    encoder = lambda x: base62_encode(x.int)

    def generate_uuid():
        the_uuid = encoder(uuid.uuid1())
        if prefix:
            the_uuid = prefix + the_uuid

        return the_uuid

    return generate_uuid
