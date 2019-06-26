import requests

# url = "https://indigo.ncats.io/reasoner/api/v1/query"
url = "https://rtx.ncats.io/beta/api/rtx/v1/query"

data1 = {
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

data2 = {
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
      "curie": "CHEMBL:CHEMBL25"
    },
    {
      "node_id": "protein",
      "type": "protein"
    }
  ]
}

json = {
    "query_message": {
        "query_graph": data2
    }
}

r = requests.post(url,json=json)

print(r,r.text)
