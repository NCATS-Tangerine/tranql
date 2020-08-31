from tranql.main import TranQL
import yaml
import os
from tranql.main import TranQLParser, set_verbose
from tranql.tranql_ast import SetStatement, custom_functions
from unittest.mock import patch
import requests_mock
import pytest

def setup_back_plane_mock():
    pass


# Mock schema
class Schema:
    def __init__(self, *args, **kwargs):
        with open(os.path.join(os.path.dirname(__file__), "mock/schema_test.yaml")) as f:
            self.schema = yaml.load(f)
            self.config = {'schema': self.schema}

    def validate_question(self, *args, **kwargs):
        return True


# Mock schema factory
class MockSchemaFactory:
    _cached = False
    _update_thread = True

    def __init__(self, **kwargs):
        self.schema = Schema()

    def get_instance(self):
        return self.schema


def setup_tranQL():
    with patch('tranql.tranql_schema.SchemaFactory', MockSchemaFactory):
        with patch('tranql.tranql_schema.Schema', Schema):
            app = TranQL()
            return app

def responses(response_type):
    return {
        'empty_answers': {
            'query_graph': {
                'nodes': [
                    {'id' : 'mmm', 'type': 'yyy'},
                    {'id' : 'mmm', 'type': 'yyy'}
                ],
            }
        }
    }.get(response_type)


def test_should_stop_if_all_kps_capable_return_nothing():
    """
    If a TranQL query with an id is passed
    the query should stop if the specified id didn't return any
    ids with the specified disease. i.e.
    :return:
    """
    app = setup_tranQL()
    query = """
    select disease->chemical_substance->gene
    FROM '/schema'
    WHERE gene='ABC:GENE'
    """
    with requests_mock.Mocker() as m:
        m.post('http://localhost:8099/source_2_1', json={'question_graph': {'nodes': [], 'edges': []},
                                                         'knowledge_graph': {'nodes': [], 'edges': []},
                                                         'knowledge_map': []})
        m.post('http://localhost:8099/source_2', json={'question_graph': {'nodes': [], 'edges': []},
                                                       'knowledge_graph': {'nodes': [], 'edges': []},
                                                       'knowledge_map': []})
        m.post('http://localhost:8099/source_1', json={'question_graph': {'nodes': [], 'edges': []},
                                                       'knowledge_graph': {'nodes': [], 'edges': []},
                                                       'knowledge_map': []})

        app.asynchronous = False
        # plan looks like
        # 1. Query source_2 & source_2_1 with disease->chemical
        # 2. Query source_1 with chemical->gene
        # In this test we have to make sure step 2 doesn't execute, since step 1 yields no results and there was a set
        # statement .

        result = app.execute(query)
        called_urls = list(map(lambda x: x.url, m.request_history))
        # source 1 should be the only one called
        assert ['http://localhost:8099/source_1'] == called_urls

def test_bound_node_service_should_be_called_first():
    query_1 = """
    select disease->chemical_substance->gene
    FROM '/schema'
    WHERE gene='GENE:1'
    """

    def set_mock_servers(m):
        m.post('http://localhost:8099/source_2_1', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
        m.post('http://localhost:8099/source_2', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
        m.post('http://localhost:8099/source_1', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
    app = setup_tranQL()
    with requests_mock.Mocker() as m:
        set_mock_servers(m)
        app.asynchronous = False
        # plan looks like
        # 1. Query source_2 & source_2_1 with disease->chemical
        # 2. Query source_1 with chemical->gene
        # In this test we have to make sure step 2 doesn't execute, since step 1 yields no results and there was a set
        # statement .
        result = app.execute(query_1)
        called_urls = list(map(lambda x: x.url, m.request_history))
        assert 'http://localhost:8099/source_1' == called_urls[0]


def test_more_complex_query_plan():
    query = """
    SELECT c1:chemical_substance->g1:gene->c2:chemical_substance<-disease->c3:phenotypic_feature
    FROM '/schema'
    WHERE c2='CHEBI:1234'
    """
    def set_mock_servers(m):
        m.post('http://localhost:8099/source_2_1', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
        m.post('http://localhost:8099/source_2', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
        m.post('http://localhost:8099/source_1', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
        m.post('http://localhost:8099/source_3', json={
            'question_graph': {'nodes': [], 'edges': []},
            'knowledge_graph': {'nodes': [], 'edges': []},
            'knowledge_map': []
        })
    with requests_mock.Mocker() as m :
        set_mock_servers(m)
        app = setup_tranQL()
        app.asynchronous = False
        app.execute(query)
        called_urls = list(map(lambda x: x.url, m.request_history))
        assert 'http://localhost:8099/source_1' in called_urls
        # due to structure of schema first query sent
        # looks like c1:chemical_substance->g1:gene->c2:chemical_substance to source_1
        # but what if source_1 is not able to answer
        # we can still continue to query on source_3 with gene->chemical_substance
        assert 'http://localhost:8099/source_3' in called_urls
        assert 'http://localhost:8099/source_2' in called_urls
        # can go from c3:chemical_substance -> disease but nothing is satisfied so should not be called.
        assert 'http://localhost:8099/source_2_1' not in called_urls





