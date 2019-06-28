import requests
import json as JSON

# This file is for testing reasoner APIs. It directly queries the selected API, not the backplane.
# (Not a unit test)

GAMMA = "https://robokop.renci.org/api/simple/quick/?max_connectivity=1000"
INDIGO = "https://indigo.ncats.io/reasoner/api/v1/query"
RTX = "https://rtx.ncats.io/beta/api/rtx/v1/query"
data1 = {
  "type":INDIGO,
  "query": {
      "edges": [
        {
          "edge_id": "e00",
          "source_id": "n00",
          "target_id": "n01",
          "type": "targets"
        }
      ],
      "nodes": [
        {
          "node_id": "n00",
          "curie": "CHEMBL:CHEMBL521",
          "type": "chemical_substance",
        },
        {
          "node_id": "n01",
          "type": "protein"
        }
      ]
  }
}
data2 = {
  "type":RTX,
  "query": {
      "edges": [
        {
          "edge_id": "e1",
          "source_id": "chemical_substance",
          "target_id": "protein"
        }
      ],
      "nodes": [
        {
          "node_id": "chemical_substance",
          "type": "chemical_substance",
          "curie":"CHEMBL.COMPOUND:CHEMBL3"
        },
        {
          "node_id": "protein",
          "type": "protein"
        }
      ]
  }
}
data3 = {
    "type":RTX,
    "query": {
        "edges": [
          {
            "edge_id": "e1",
            "source_id": "metabolite",
            "target_id": "protein"
          }
        ],
        "nodes": [
          {
            "node_id": "metabolite",
            "type": "metabolite",
            "curie":"KEGG:C00017"
          },
          {
            "node_id": "protein",
            "type": "protein"
          }
        ]
    }
}

data4 = {
    "type":RTX,
    "query": {
        "edges": [
          {
            "edge_id": "e1",
            "source_id": "disease",
            "target_id": "phenotypic_feature"
          }
        ],
        "nodes": [
          {
            "node_id": "disease",
            "type": "disease"
          },
          {
            "node_id": "phenotypic_feature",
            "type": "phenotypic_feature",
            "curie":"HP:0005978"
          }
        ]
    }
}

data5 = {
    "type": GAMMA,
    "query": {
    "question_graph": {
        "edges": [
            {
            "id": "e1",
            "source_id": "chemical_substance",
            "target_id": "disease"
            }
        ],
        "nodes": [
            {
                "id": "chemical_substance",
                "type": "chemical_substance",
                "curie": [
                    "CHEMBL:CHEMBL3"
                ]
            },
            {
                "id": "disease",
                "type": "disease"
            }
        ]
    }
}
}

data6 = {
    "type": INDIGO,
    "query": {
        "edges": [
            {
              "source_id": "chemical_substance",
              "target_id": "gene",
              "edge_id": "e1"
            }
          ],
          "nodes": [
            {
              "type": "chemical_substance",
              "curie": "CHEMBL:CHEMBL3",
              "node_id": "chemical_substance"
            },
            {
              "type": "gene",
              "node_id": "gene"
            }
          ]
    }
}

data7 = {
    "type":RTX,
    "query": {
        "edges": [
          {
            "edge_id": "e1",
            "source_id": "disease",
            "target_id": "biological_process"
          }
        ],
        "nodes": [
          {
            "node_id": "disease",
            "type": "chemical_substance",
            "curie": "CHEMBL.COMPOUND:CHEMBL1261"
          },
          {
            "node_id": "biological_process",
            "type": "disease"
          }
        ]
    }
}

active_query = data7

if active_query["type"] == INDIGO or active_query["type"] == RTX:
    json = {
        "query_message": {
            "query_graph": active_query["query"]
        }
    }
elif active_query["type"] == GAMMA:
    json = active_query["query"]
r = requests.post(active_query["type"],json=json)

print(r.status_code,r.ok,r.text)
