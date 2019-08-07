import requests
import requests_mock as r_mock
from tranql.tests.mocks import MockMap

def assert_lists_equal (a, b):
    """ Assert the equality of two lists. """
    assert len(a) == len(b)
    for index, expected in enumerate(a):
        actual = b[index]
        if isinstance(actual,str) and isinstance(expected, str) and \
           actual.isspace() and expected.isspace ():
            continue
        elif isinstance(actual, list) and isinstance(expected, list):
            assert_lists_equal (actual, expected)
        else:
            assert actual == expected

def set_mock (requests_mock, name):
    mock_map = MockMap (requests_mock, name)
    session = requests.Session()
    adapter = r_mock.Adapter()
    session.mount('requests_mock', adapter)

def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj
