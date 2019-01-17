from enum import Enum
import re
import binascii

"""
@/path/to/file
"string'
0x010203
b64YmFzZTY0
"""


class Type(Enum):
    STRING = 0,
    HEX = 1,
    BASE64 = 2,
    FILE = 3


__type_mapping = {
    '"': Type.STRING,
    '0x': Type.HEX,
    'b64': Type.BASE64,
    '@': Type.FILE,
    '@"': Type.FILE
}


def __parse_string(parameter):
    match = re.fullmatch('"(.*)"', parameter)
    assert match is not None
    return match.group(1).encode('ascii')


def __parse_hex(parameter):
    match = re.fullmatch('0x(([a-fA-F0-9]{2})+)', parameter)
    assert match is not None
    return binascii.unhexlify(match.group(1))


def __parse_b64(parameter):
    match = re.fullmatch('b64(.+)', parameter)
    assert match is not None
    return binascii.a2b_base64(match.group(1))


def __parse_file(parameter):
    return b'0'


__type_parsing = {
    Type.STRING: __parse_string,
    Type.HEX: __parse_hex,
    Type.BASE64: __parse_b64,
    Type.FILE: __parse_file
}

pattern_string = '".{1,}"'
pattern_file = '@[\\/\\w]{1,}'
pattern_file_quoted = '@".{1,}"'
pattern_b64 = 'b64\\w{1,}={0,2}'


def parse(parameter: str):
    print(parameter)
    type_regex = '(%s)' % '|'.join(__type_mapping)
    print(type_regex)
    type_match = re.match(type_regex, parameter)

    if type_match is None:
        return None

    parameter_type = __type_mapping.get(type_match.group(1))

    return __type_parsing.get(parameter_type)(parameter)
