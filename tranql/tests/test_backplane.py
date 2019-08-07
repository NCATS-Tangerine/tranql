import pytest
import json
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.backplane.server import api, app

@pytest.fixture
def client():
    client = app.test_client()
    yield client

# def 
