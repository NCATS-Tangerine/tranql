import pytest
import json
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.exception import TranQLException
from tranql.api import api, app, StandardAPIResource

@pytest.fixture
def client():
    client = app.test_client()
    yield client

"""
[util]
"""
def test_decorate_kg (client):
    knowledge_graph = {
      "edges": [
        {
          "id": "e0",
          "source_id": "n0",
          "target_id": "n1",
          "type": "targets"
        }
      ],
      "nodes": [
        {
          "id": "n0",
          "type": "chemical_substance"
        },
        {
          "id": "n1",
          "type": "gene"
        }
      ]
    }
    expected = {
      "edges": [
        {
          "id": "e0",
          "source_id": "n0",
          "target_id": "n1",
          "type": "targets",
          "reasoner": [
            "robokop"
          ],
          "source_database": [
            "unknown"
          ]
        }
      ],
      "nodes": [
        {
          "id": "n0",
          "type": "chemical_substance",
          "reasoner": [
            "robokop"
          ]
        },
        {
          "id": "n1",
          "type": "gene",
          "reasoner": [
            "robokop"
          ]
        }
      ]
    }
    args = {
        'reasoners' : ['robokop']
    }
    response = client.post(
        f'/tranql/decorate_kg',
        query_string=args,
        data=json.dumps(knowledge_graph),
        content_type='application/json'
    )
    assert ordered(response.json) == ordered(expected)

def test_merge_messages (client):
    messages = [
      {
        "knowledge_graph": {
          "edges": [
            {
              "source_id": "TEST:CS1",
              "target_id": "TEST:G1",
              "type": "targets"
            }
          ],
          "nodes": [
            {
              "id": "TEST:CS1",
              "type": "chemical_substance"
            },
            {
              "id": "TEST:G1",
              "type": "gene"
            }
          ]
        }
      },
      {
        "knowledge_graph": {
          "edges": [
            {
              "source_id": "TEST:CS2",
              "target_id": "TEST:G2",
              "type": "interacts_with"
            }
          ],
          "nodes": [
            {
              "equivalent_identifiers": [
                "TEST:CS1"
              ],
              "id": "TEST:merged",
              "type": [
                "chemical_substance",
                "Drug"
              ]
            },
            {
              "id": "TEST:CS2",
              "type": "chemical_substance"
            },
            {
              "id": "TEST:G2",
              "type": "gene"
            }
          ]
        }
      }
    ]
    expected = {
      "knowledge_graph": {
        "nodes": [
          {
            "id": "TEST:CS1",
            "type": [
              "chemical_substance",
              "Drug"
            ],
            "equivalent_identifiers": [
              "TEST:merged",
              "TEST:CS1"
            ]
          },
          {
            "id": "TEST:G1",
            "type": [
              "gene"
            ],
            "equivalent_identifiers": [
              "TEST:G1"
            ]
          },
          {
            "id": "TEST:CS2",
            "type": [
              "chemical_substance"
            ],
            "equivalent_identifiers": [
              "TEST:CS2"
            ]
          },
          {
            "id": "TEST:G2",
            "type": [
              "gene"
            ],
            "equivalent_identifiers": [
              "TEST:G2"
            ]
          }
        ],
        "edges": [
          {
            "source_id": "TEST:CS1",
            "target_id": "TEST:G1",
            "type": [
              "targets"
            ]
          },
          {
            "source_id": "TEST:CS2",
            "target_id": "TEST:G2",
            "type": [
              "interacts_with"
            ]
          }
        ]
      },
      "knowledge_map": [],
      "question_graph": {
        "nodes": [],
        "edges": []
      }
    }
    args = {
        'name_based_merging': True,
        'resolve_names': False
    }
    response = client.post(
        f'/tranql/merge_messages',
        query_string=args,
        data=json.dumps(messages),
        content_type='application/json'
    )

    assert ordered(response.json) == ordered(expected)

"""
[schema]
"""
def test_schema(client, requests_mock):
    set_mock(requests_mock, "workflow-5")
    response = client.get('/tranql/schema').json
    assert 'schema' in response
    assert 'knowledge_graph' in response['schema']

def test_model_concepts(client, requests_mock):
    response = client.post('/tranql/model/concepts')
    assert isinstance(response.json,list)
    assert "RNA_product" in response.json

def test_model_relations(client, requests_mock):
    response = client.post('/tranql/model/relations')
    assert isinstance(response.json,list)
    assert "affects" in response.json

"""
[validation]
"""
def test_query(client, requests_mock):
    set_mock(requests_mock, "workflow-5")
    program = """
        --
        -- Workflow 5
        --
        --   Modules 1-4: Chemical Exposures by Clinical Clusters
        --      For sub-clusters within the overall ICEES asthma cohort defined by
        --      differential population density, which chemicals are related to these
        --      clusters with a p_value less than some threshold?
        --
        --   Modules 5-*: Knowledge Graph Phenotypic Associations
        --      For chemicals produced by the first steps, what phenotypes are
        --      associated with exposure to these chemicals?
        --
        SET id_filters = "SCTID,rxcui,CAS,SMILES,umlscui"

        SELECT population_of_individual_organisms->drug_exposure
          FROM "/clinical/cohort/disease_to_chemical_exposure"
         WHERE EstResidentialDensity < '2'
           AND population_of_individual_organizms = 'x'
           AND cohort = 'all_patients'
           AND max_p_value = '0.1'
           SET '$.knowledge_graph.nodes.[*].id' AS chemical_exposures

        SELECT chemical_substance->gene->biological_process->phenotypic_feature
          FROM "/graph/gamma/quick"
         WHERE chemical_substance = $chemical_exposures
           SET knowledge_graph
    """
    args = {
        "dynamic_id_resolution" : True,
        "asynchronous" : False
    }
    response = client.post(
        '/tranql/query',
        query_string=args,
        data=program,
        content_type='application/json'
    )
    assert 'message' not in response.json
    assert 'errors' not in response.json
    assert response.json['knowledge_graph']['nodes'][0]['id'] == "CHEBI:28177"
    assert response.json['knowledge_map'][0]['node_bindings']['chemical_substance'] == "CHEBI:28177"

    response = client.post(
        '/tranql/query',
        query_string=args,
        data="""
            SELECT chemical_substance->foobar
              FROM '/schema'
        """,
        content_type='application/json'
    )

    assert response.status_code == 500
    assert response.json['status'] == 'Error'

# def test_root (client):
    # assert client.get('/').status_code == 200

def test_standard_api_resource(client, requests_mock):
    assert ordered(StandardAPIResource.handle_exception(
        [
            Exception('foo'),
            TranQLException('bar',details='baz')
        ],
        warning=True
    )) ==  ordered({
        "errors" : [
            {
                "message" : "foo",
                "details" : ""
            },
            {
                "message" : "bar",
                "details" : "baz"
            }
        ],
        "status" : "Warning"
    })

    assert StandardAPIResource.response({
        'status' : 'Warning',
        'errors' : [],
        'knowledge_graph' : {
            'nodes' : [],
            'edges' : []
        }
    }) == (
        {
        'status' : 'Warning',
        'errors' : [],
        'knowledge_graph' : {
            'nodes' : [],
            'edges' : []
        }
        },
        200
    )

    assert StandardAPIResource.response({
        'status' : 'Error',
        'errors' : []
    }) == (
        {
        'status' : 'Error',
        'errors' : []
        },
        500
    )
