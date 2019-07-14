import networkx as nx
import json
import yaml
import logging
import requests
import requests_cache
import os
from tranql.concept import BiolinkModelWalker
from collections import defaultdict
from tranql.exception import TranQLException, InvalidTransitionException
from tranql.redis_graph import RedisGraph

class NetworkxGraph:
    def __init__(self):
        self.net = nx.MultiDiGraph ()
    def add_edge (self, start, predicate, end, properties={}):
        return self.net.add_edge (start, end, key=predicate, **properties)
    def add_node (self, identifier, label=None, properties={}):
        return self.net.add_node (identifier, attr_dict=properties)
    def has_node (self, identifier):
        return identifier in self.net.nodes
    def get_node (self, identifier, properties=None):
        return self.net.nodes [identifier]
    def get_edge (self, start, end, properties=None):
        result = None
        for e in self.net.edges:
            #print (f"-----    {start} {end} | {e[0]} {e[2]}")
            if e[0] == start and e[1] == end:
                result = e
                break
        return result
    def get_nodes (self,**kwargs):
        return self.net.nodes(**kwargs)
    def get_edges (self,**kwargs):
        return self.net.edges(keys=True,**kwargs)
    def delete (self):
        self.net.clear ()
    def commit (self):
        pass

class GraphTranslator:
    """
    An interface to a knowledge graph.
      - Support a general underlying graph interface with plugins for different
        in-memory or persistent implementations.
      - Support writing and reading graphs to multiple formats.
    """
    def __init__(self, graph):
        """ Connect to an abstract graph interface. """
        self.graph = graph

    def write_kgs (self, message):
        """ Write KGS message to the graph.
        :param message: Get a knowledge graph as a network.
        :return: Return a network.
        """
        kg = message['knowledge_graph']
        nodes = kg['nodes']
        edges = kg['edges']
        for n in nodes:
            self.graph.add_node(n['id'], properties=n)
        for e in edges:
            self.graph.add_edge (e['source_id'], e['target_id'], properties=e)
        return g

    def graph_to_message(self):
        """
        Write underlying graph interface to a KGS message
        :return: Return a KGS message
        """
        nodes = list (self.graph.get_nodes ())
        edges = list (self.graph.get_edges (data=True))
        return {
            "knowledge_graph" : {
                "nodes" : nodes,
                "edges" : edges
            },
            "knowledge_maps" : [
                {}
            ],
            "options" : {}
        }

class Schema:
    """ A schema for a distributed knowledge network. """

    def __init__(self, backplane):
        """
        Create a metadata map of the knowledge network.
        """

        # String[] of errors encountered during loading.
        self.loadErrors = []

        """ Load the schema, a map of reasoner systems to maps of their schemas. """
        self.config = None
        config_file = os.path.join (os.path.dirname(__file__), "conf", "schema.yaml")
        with open(config_file) as stream:
            self.config = yaml.safe_load (stream)

        """ Resolve remote schemas. """
        for schema_name, metadata in self.config['schema'].copy ().items ():
            schema_data = metadata['schema']
            if isinstance (schema_data, str) and schema_data.startswith ("/"):
                schema_data = f"{backplane}{schema_data}"
            if isinstance(schema_data, str) and schema_data.startswith('http'):
                # If schema_data is a URL
                try:
                    response = requests.get (schema_data)
                    schema_data = response.json()
                except requests.exceptions.RequestException as e:
                    # If the request errors for any number of reasons (likely a timeout), append an error message
                    if isinstance(e,requests.exceptions.Timeout):
                        error = 'Request timed out while fetching schema at "'+schema_data+'"'
                    elif isinstance(e,requests.exceptions.ConnectionError):
                        error = 'Request could not connect while fetching schema at "'+schema_data+'"'
                    else:
                        error = 'Request failed while fetching schema at "'+schema_data+'"'
                    self.loadErrors.append(error)
                    # Delete the key here because it has no data.
                    del self.config['schema'][schema_name]
                    continue
            # Else, it must already be loaded
            metadata['schema'] = schema_data
            self.config['schema'][schema_name] = metadata
        self.schema = self.config['schema']

        """ Build a graph of the schema. """
        #self.schema_graph = RedisGraph ()
        self.schema_graph = NetworkxGraph ()
        try:
            self.schema_graph.delete ()
        except:
            pass

        for k, v in self.config['schema'].items ():
            #print (f"layer: {k}")
            self.add_layer (layer=v['schema'], name=k)

        self.schema_graph.commit ()

    def add_layer (self, layer, name=None):
        """
        :param layer: Knowledge schema metadata layers.
        """
        for source_name, targets_list in layer.items ():
            source_node = self.get_node (node_id=source_name)
            for target_type, links in targets_list.items ():
                target_node = self.get_node (node_id=target_type)
                #self.schema_graph.commit ()
                if isinstance(links, str):
                    links = [links]
                for link in links:
                    #print (f" {source_name}->{target_type} [{link}]")
                    self.schema_graph.add_edge (source_name, link, target_type, {"provided_by":name})

    def get_edge (self, plan, source_name, source_type, target_name, target_type,
                  predicate, edge_direction):
        """ Determine if a transition between two types is supported by
        any of the registered sub-schemas.
        """
        edge = None
        schema = None
        for schema_name, sub_schema_package in self.schema.items ():
            sub_schema = sub_schema_package ['schema']
            sub_schema_url = sub_schema_package ['url']
            #print (sub_schema)
            if source_type in sub_schema:
                print (f"  --{schema_name} - {source_type} => {target_type}")
                if target_type in sub_schema[source_type]:
                    top_schema = None
                    if len(plan) > 0:
                        top = plan[-1]
                        top_schema = top[0]
                    if top_schema == schema_name:
                        # this is the next edge in an ongoing segment.
                        top[2].append ([ source_name, source_type,
                                         predicate, edge_direction,
                                         target_name, target_type ])
                    else:
                        plan.append ([ schema_name, sub_schema_url, [
                            [ source_name, source_type,
                              predicate, edge_direction,
                              target_name, target_type ]
                        ]])
            else:
                implicit_conversion = BiolinkModelWalker ()
                for conv_type in implicit_conversion.get_transitions (source_type):
                    implicit_conversion_schema = "implicit_conversion"
                    implicit_conversion_url = self.schema[implicit_conversion_schema]['url']
                    if conv_type in sub_schema:
                        print (f"  --impconv: {schema_name} - {conv_type} => {target_type}")
                        if target_type in sub_schema[conv_type]:
                            plan.append ([
                                implicit_conversion_schema,
                                implicit_conversion_url,
                                [
                                    [ source_name, source_type,
                                      predicate, edge_direction,
                                      conv_type, conv_type ]
                                ]])
                            plan.append ([ schema_name, sub_schema_url, [
                                [ conv_type, conv_type,
                                  predicate, edge_direction,
                                  target_name, target_type ]
                            ]])

    def plan (self, query):
        """
        Plan a query over the configured sources and their associated schemas.
        Build a structure like this:
           source_type
              target_type
                 source
                 transition
        Start with: Linear paths; no predicates.
        """
        print (query)
        plan = []
        #plan = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for index, element_name in enumerate(query.order):
            if index == len(query.order) - 1:
                """ There's another concept to transition to. """
                continue
            self.get_edge (
                plan=plan,
                source_name = element_name,
                source_type=query.concepts[element_name].name,
                target_name = query.order[index+1],
                target_type=query.concepts[query.order[index+1]].name,
                predicate=query.arrows[index].predicate,
                edge_direction=query.arrows[index].direction)
        print (f"----------> {json.dumps(plan, indent=2)}")
        return plan

    def get_node (self, node_id, attrs={}):
        """ Get a node if it exists; create one if it doesn't.
        :param node_id: Unique id of the node.
        :return: Return the node designated by this identifier.
        """
        #return self.knet.nodes [node_id] if node_id in self.knet.nodes else \
        #    self.knet.add_node (node_id, attr_dict=attrs)
        return self.schema_graph.get_node (node_id, attrs) if \
            self.schema_graph.has_node (node_id) else \
            self.schema_graph.add_node (
                label="thing",
                identifier=node_id,
                properties=attrs)

    def validate_edge (self, source_type, target_type):
        """
        Assert that there is an edge between these types in the schema.
        :param source_type: A source type.
        :param target_type: A target type.
        """
        edge = self.schema_graph.get_edge (start=source_type, end=target_type)
        if not edge:
            raise InvalidTransitionException (source_type, target_type)

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
            # print (f"  -- valid transition: {source}->{target}")


def get_test_kg (file_name):
    path = "https://raw.githubusercontent.com/NCATS-Tangerine/NCATS-ReasonerStdAPI-diff/master"
    url = f"{path}/{file_name}"
    print (url)
    return requests.get (url).json ()


def main ():
    """ Process arguments. """
    arg_parser = argparse.ArgumentParser(
        description='TranQL Schema',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(
            prog,
            max_help_position=180))
    arg_parser.add_argument('-s', '--create-schema', help="Create the schema.", action="store_true")
    args = arg_parser.parse_args ()
    if args.create_schema:
        print ('yeah')

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
'''
requests_cache.install_cache('meta_cache')
m = Schema ()
m.validate_question (test_question)
'''

#m.validate_question (get_test_kg ("albuterol_wf5_results.json"))
#m.validate_question (get_test_kg ("albuterol_wf5_results_gamma.json"))
# cornerstone
# slicer
