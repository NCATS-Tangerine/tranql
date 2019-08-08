import pytest
import json
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.backplane.server import api, app
from tranql.backplane.server import RtxQuery

@pytest.fixture
def client():
    client = app.test_client()
    yield client

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
                    "chemical_substance" : ["CHEMBL:CHEMBL3"]
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
