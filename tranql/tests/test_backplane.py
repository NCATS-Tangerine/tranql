import pytest
import json
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.backplane.server import api, app
from tranql.backplane.server import RtxQuery, ICEESClusterQuery, GammaQuery
import requests_mock

@pytest.fixture
def client():
    client = app.test_client()
    yield client

def test_robokop_paramter_are_picked_up():
    import os
    os.environ['ROBOKOP_MAX_CONNECTIVITY'] = "1"
    os.environ['ROBOKOP_MAX_RESULTS'] = "1"
    gamma_query = GammaQuery()
    assert gamma_query.quick_url == 'https://robokop.renci.org/api/simple/quick/?' \
            f'rebuild=false&' \
            f'output_format=MESSAGE&' \
            f'max_connectivity=1&' \
            f'max_results=1'


def test_rtx_convert_curies(client):
    converted_to_rtx = RtxQuery.convert_curies_to_rtx({
        "question_graph" : {
            "nodes" : [
                {
                    "curie" : "CHEMBL:CHEMBL3",
                    "id" : "chemical_substance",
                    "type" : "chemical_substance"
                }
            ],
            "edges" : []
        }
    })
    assert ordered(converted_to_rtx) == ordered({
        "question_graph" : {
            "nodes" : [
                {
                    "curie" : "CHEMBL.COMPOUND:CHEMBL3",
                    "id" : "chemical_substance",
                    "type" : "chemical_substance"
                }
            ],
            "edges" : []
        }
    })
    converted_to_standard = RtxQuery.convert_curies_to_standard({
        "knowledge_map" : [
            {
                "node_bindings" : {
                    "chemical_substance" : ["CHEMBL.COMPOUND:CHEMBL3"]
                },
                "edge_bindings" : {
                    "foo" : [""]
                }
            }
        ],
        "knowledge_graph" : {
            "nodes" : [
                {
                    "id" : "CHEMBL.COMPOUND:CHEMBL3"
                },
                {
                    "id" : "FOOBAR"
                }
            ],
            "edges" : [
                {
                    "source_id" : "CHEMBL.COMPOUND:CHEMBL3",
                    "target_id" : "FOOBAR"
                }
            ]
        },
        "question_graph" : {
            "nodes" : [
                {
                    "curie" : "CHEMBL.COMPOUND:CHEMBL3",
                    "id" : "chemical_substance",
                    "type" : "chemical_substance"
                }
            ],
            "edges" : []
        }
    })
    assert ordered(converted_to_standard) == ordered({
        "knowledge_map" : [
            {
                "node_bindings" : {
                    "chemical_substance" : "CHEMBL:CHEMBL3"
                },
                "edge_bindings" : {
                    "foo" : [""]
                }
            }
        ],
        "knowledge_graph" : {
            "nodes" : [
                {
                    "id" : "CHEMBL:CHEMBL3"
                },
                {
                    "id" : "FOOBAR"
                }
            ],
            "edges" : [
                {
                    "source_id" : "CHEMBL:CHEMBL3",
                    "target_id" : "FOOBAR"
                }
            ]
        },
        "question_graph" : {
            "nodes" : [
                {
                    "curie" : "CHEMBL:CHEMBL3",
                    "id" : "chemical_substance",
                    "type" : "chemical_substance"
                }
            ],
            "edges" : []
        }
    })

# def test_rtx_query(client):
#     response = client.post(
#         '/graph/rtx'
#         data=json.dumps()
#         content_type='application/json'
#     )

def test_icees_synonymzation():
    icees_response = {
        'question_graph': {
            'nodes': [
                {'id': 'node_1', 'type': 'unsupported_type'},
                {'id': 'node_2', 'type': 'supported_type_1'},
                {'id': 'node_3', 'type': 'supported_type_2'}
            ],
            'edges': [
                {'id': 'edge_1_2', 'source_id': 'node_1', 'target_type': 'node_2'},
                {'id': 'edge_2_3', 'source_id': 'node_2', 'target_type': 'node_3'}
            ]
        },
        'knowledge_graph': {
            'nodes': [
                {'id': 'curie:1', 'name': 'some_name', 'type': 'unsupported_type'},
                {'id': 'curie:2', 'name': 'some_name', 'type': 'supported_type_1'},
                {'id': 'curie:3', 'name': 'some_name', 'type': 'supported_type_1_subtype_1'},
                {'id': 'curie:4', 'name': 'curie_4_name', 'type': 'supported_type_2'},
                {'id': 'curie:5', 'name': 'curie_4_name', 'type': 'supported_type_2'}
            ],
            'edges': [
                {'id': 'edge_curie:1_curie:2', 'source_id': 'curie:1', 'target_id': 'curie:2'},
                {'id': 'edge_curie:2_curie:4', 'source_id': 'curie:2', 'target_id': 'curie:4'},
                {'id': 'edge_curie:1_curie:3', 'source_id': 'curie:1', 'target_id': 'curie:3'},
                {'id': 'edge_curie:3_curie:4', 'source_id': 'curie:3', 'target_id': 'curie:4'},
                {'id': 'edge_curie:3_curie:5', 'source_id': 'curie:3', 'target_id': 'curie:5'}
            ]
        }
    }
    answer1, answer2, answer3 = \
        {
                'node_bindings': {'node_1': 'curie:1', 'node_2': 'curie:2', 'node_3': 'curie:4'},
                'edge_bindings': {'edge_1_2': ['edge_curie:1_curie:2'], 'edge_3_4': ['edge_curie:2_curie:4']}
        }\
        ,{
            'node_bindings': {'node_1': 'curie:1', 'node_2': 'curie:3', 'node_3': 'curie:4'},
            'edge_bindings': {'edge_1_2': ['edge_curie:1_curie:2'], 'edge_3_4': ['edge_curie:3_curie:4']}
        }\
        ,{
            'node_bindings': {'node_1': 'curie:1', 'node_2': 'curie:3', 'node_3': 'curie:5'},
            'edge_bindings': {'edge_1_2': ['edge_curie:1_curie:3'], 'edge_3_4': ['edge_curie:3_curie:5']}
        }
    icees_response['knowledge_map'] = [answer1, answer2, answer3]

    # For icees we will treat nodes in 3 categories
    # nodes that are typed as types that are not supported by node normalization service
    # nodes that are typed can be as ones that normalize and ones that don't
    # our test is to make sure all nodes that are either normalizable or are don't have supported to be
    # kept in the knowledge graph and nodes of supported type that donot normalize are dropped.

    # mocking node norm get semantic types response
    get_semantic_types_response = {
      "semantic_types": {
        "types": [
            "supported_type_1",
            "supported_type_2"
        ]
      }
    }
    # lets say curie:5 is unknown to the normalization service
    # and curie:2 has its name updated
    # and curie:3 has new id curie:33
    # and curie:4 has same id but missing label in its normalized id but one eq has label

    get_normalized_curies_response = {
        "curie:2": {
            "id": {
                "identifier": "curie:2",
                "label": "curie_2 has its name_updated"
            },
            "equivalent_identifiers": [
                {"identifier": "curie:2", "label": "curie_2 has updated name"}
            ]
        },
        "curie:3": {
            "id": {
                "identifier": "curie:33",
                "label": "new label"
            },
            "equivalent_identifiers": [
                {"identifier": "curie:3",  "label": "some_name"},
                {"identifier": "curie:33", "label": "new label"}
            ]
        },
        "curie:4": {
            "id":{
                "identifier": "curie:4",
                "label": ""
            },
            "equivalent_identifiers": [
                {"identifier": "curie:4", "label": ""},
                {"identifier": "curie:44", "label": "updated name"}
            ]
        }
    }
    curie_params = '&'.join([f'curie={x["id"]}' for x in icees_response['knowledge_graph']['nodes']])
    with requests_mock.mock() as mock_server:
        mock_server.get(
            'https://nodenormalization-sri.renci.org/get_semantic_types',
            json=get_semantic_types_response
        )

        mock_server.get(
            f'https://nodenormalization-sri.renci.org/get_normalized_nodes',
            json=get_normalized_curies_response
        )

        mock_server.get(
            f'https://bl-lookup-sri.renci.org/bl/supported_type_1/descendants?version=latest',
            json = [
                'supported_type_1_subtype_1'
            ]
        )
        mock_server.get(
            f'https://bl-lookup-sri.renci.org/bl/supported_type_2/descendants?version=latest',
            json=[
                'supported_type_2'
            ]
        )

        icees_cluster_class = ICEESClusterQuery()

        result = icees_cluster_class.synonymize(icees_response)

        # we expect answer 3 to be gone so as node 5 and the edge 3->5 (edge_id : 'edge_curie:3_curie:5') to be removed
        assert len(result['knowledge_graph']['edges']) == 4
        assert 'edge_curie:3_curie:5' not in [edge['id'] for edge in result['knowledge_graph']['edges']]

        assert len(result['knowledge_graph']['nodes']) == 4
        node_ids = [node['id'] for node in result['knowledge_graph']['nodes']]
        node_ids_expected = ['curie:1', 'curie:2', 'curie:33', 'curie:4']
        assert 'curie:5' not in node_ids
        for n_id in node_ids_expected:
            assert n_id in node_ids

        labels =  {node['id']: node['name'] for node in result['knowledge_graph']['nodes']}
        expected_labels = {
         'curie:1':'some_name',
         'curie:2': 'curie_2 has its name_updated',
         'curie:33': 'new label',
         'curie:4': 'updated name'
        }
        for node_id in labels:
            assert labels[node_id] == expected_labels[node_id]


        # check if ids are updated in knowledge map

        assert len(result['knowledge_map']) == 2
        # we expect answer 1 not to change
        assert answer1 in result['knowledge_map']
        # we expect the other other to have curie:3 (bound to q_id node_2 to be updated)
        next_answer = list(filter(lambda x: x != answer1, result['knowledge_map']))[0]
        assert next_answer['node_bindings']['node_2'] == 'curie:33'
        # assert the edge source and targe binding node_2 and node_3 is updated
        edge_id = next_answer['edge_bindings']['edge_3_4']
        edge = [e for e in result['knowledge_graph']['edges'] if e['id'] in edge_id][0]
        assert edge['source_id'] == 'curie:33'


