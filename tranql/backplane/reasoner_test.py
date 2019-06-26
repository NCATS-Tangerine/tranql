import requests
import json as JSON

# This file is for testing reasoner APIs. It directly queries the selected API, not the backplane.
# (Not a unit test)

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
          "curie":"CHEMBL.COMPOUND:CHEMBL25"
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

active_query = data4

if active_query["type"] == INDIGO or active_query["type"] == RTX:
    json = {
        "query_message": {
            "query_graph": active_query["query"]
        }
    }
r = requests.post(active_query["type"],json=json)

print(r,r.text)
