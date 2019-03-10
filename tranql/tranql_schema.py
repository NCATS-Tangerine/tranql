import networkx as nx
import json
import yaml
import requests
import requests_cache
import os
from tranql.exception import TranQLException

class Schema:
    """ A schema for a distributed knowledge network. """
    
    def __init__(self):
        """
        Create a metadata map of the knowledge network.
        """

        """ A map of reasoner-like systems to maps of their knowledge schema. """
        config_file = os.path.join (os.path.dirname(__file__), "conf", "schema.yaml")
        self.config = None
        with open(config_file) as stream:
            self.config = yaml.safe_load (stream)
            #print (json.dumps(config, indent=2))

        schema = self.config.get ("schema", {}).get("layers", {})
        imports = self.config.get ("schema", {}).get ("import", {})

        for source, conf in imports.items ():
            layer_schema = conf['schema']
            layer_schema = requests.get (layer_schema).json () \
                           if layer_schema.startswith('http') else \
                              layer_schema
            schema[source] = {
                "url" : conf['url'],
                "schema" : layer_schema
            }
            
        """ Build a graph of the schema. """
        self.knet = nx.MultiDiGraph ()
        for k, v in self.config['schema']['layers'].items ():
            self.add_meta_layer (
                layer=v['schema'])  #requests.get (v['url']).json ())
        #for k, v in self.layer.items ():
        #    self.add_meta_layer (v)
        for k, v in schema.items ():
            self.add_meta_layer (v["schema"])

        
    def add_meta_layer (self, layer):
        """
        :param layer: Knowledge schema metadata layers.
        """
        for source_name, targets_list in layer.items ():
            source_node = self.get_node (source_name)
            for target_type, links in targets_list.items ():
                target_node = self.get_node (target_type)
                if isinstance(links, list):
                    for link in links:
                        print (f" {source_name}->{target_type} [{link}]")
                        self.knet.add_edge (source_name,
                                            target_type,
                                            key=link['link'])
                elif isinstance(links, str):
                    print (f" {source_name}->{target_type} [{link}]")
                    self.knet.add_edge (source_name,
                                        target_type,
                                        key=links)
    def plan_query (self, query):
        pass
    
    def get_node (self, node_id, attrs={}):
        """ Get a node if it exists; create one if it doesn't.
        :param node_id: Unique id of the node.
        :return: Return the node designated by this identifier.
        """
        return self.knet.nodes [node_id] if node_id in self.knet.nodes else \
            self.knet.add_node (node_id, attr_dict=attrs)

    def get_kg_network (self, message):
        """ Answer to networkx.
        :param message: Get a knowledge graph as a network.
        :return: Return a network.
        """
        kg = message['knowledge_graph']
        nodes = kg['nodes']
        edges = kg['edges']
        g = nx.MultiDiGraph()
        for n in nodes:
            g.add_node(n['id'], attr_dict=n)
        for e in edges:
            g.add_edge (e['source_id'], e['target_id'], attr_dict=e)
        return g

    def validate_edge (self, source_type, target_type):
        """
        Assert that there is an edge between these types in the schema.
        :param source_type: A source type.
        :param target_type: A target type.
        """
        valid = False
        for e in self.knet.edges:
            if e[0] == source_type and e[1] == target_type:
                valid = True
        if not valid:
            raise TranQLException (f"Invalid transition: {source_type}->{target_type}")
        
    def validate_question (self, message):
        """
        Validate the question in a message object.
        :param message: Validate the edges in the question.
        """
        question = message['question_graph']
        nodes = { n['id'] : n for n in question['nodes'] }
        for edge in question['edges']:
            source = nodes[edge['source_id']]['type']
            target = nodes[edge['target_id']]['type']
            self.validate_edge (source, target)
            print (f"  -- valid transition: {source}->{target}")

def get_test_kg (file_name):
    path = "https://raw.githubusercontent.com/NCATS-Tangerine/NCATS-ReasonerStdAPI-diff/master"
    url = f"{path}/{file_name}"
    print (url)
    return requests.get (url).json ()

test_question = {
  "question_graph": {
    "edges": [
      {
        "id": "e0",
        "source_id": "n0",
        "target_id": "n1"
      },
      {
        "id": "e1",
        "source_id": "n1",
        "target_id": "n2"
      },
      {
        "id": "e2",
        "source_id": "n2",
        "target_id": "n3"
      },
      {
        "id": "e3",
        "source_id": "n4",
        "target_id": "n3"
      }
    ],
    "nodes": [
      {
        "id": "n0",
        "type": "chemical_substance",
        "curie": "PUBCHEM:2083"
      },
      {
        "id": "n1",
        "type": "gene"
      },
      {
        "id": "n2",
        "type": "anatomical_entity"
      },
      {
        "id": "n3",
        "type": "phenotypic_feature"
      },
      {
        "id": "n4",
        "type": "disease",
        "curie": "MONDO:0004979"
      }
    ]
  },
  "knowledge_graph": {
    "nodes": [],
    "edges": []
  },
  "knowledge_maps": [
    {}
  ],
  "options": {}
}
requests_cache.install_cache('meta_cache')
m = Schema ()
m.validate_question (test_question)
#m.validate_question (get_test_kg ("albuterol_wf5_results.json"))
#m.validate_question (get_test_kg ("albuterol_wf5_results_gamma.json"))
