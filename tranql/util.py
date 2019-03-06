import copy
import logging
import logging.config
import importlib
import json
import traceback
import unittest
import datetime
import os
import re
from collections import namedtuple
import copy
import yaml
from jsonpath_rw import parse

logger = logging.getLogger("util")
logger.setLevel(logging.WARNING)

class LoggingUtil(object):
    """ Logging utility controlling format and setting initial logging level """
    @staticmethod
    def init_logging (name, level=logging.INFO, format='short'):
        logger = logging.getLogger(__name__)
        if not logger.parent.name == 'root':
            return logger

        FORMAT = {
            "short" : '%(funcName)s: %(message)s',
            "medium" : '%(funcName)s: %(asctime)-15s %(message)s',
            "long"  : '%(asctime)-15s %(filename)s %(funcName)s %(levelname)s: %(message)s'
        }[format]
        handler = logging.StreamHandler()
        formatter = logging.Formatter(FORMAT)
        handler.setFormatter(formatter)
        logger = logging.getLogger (name)
        logger.addHandler(handler)
        logger.setLevel(level)
        return logger

    @staticmethod
    def setup_logging(
            default_path=os.path.join(os.path.dirname(__file__), 'logging.yaml'),
            default_level=logging.INFO,
            env_key='LOG_CFG'):
        """Setup logging configuration
        
        """
        path = default_path
        value = os.getenv(env_key, None)
        if value:
            path = value
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.safe_load(f.read())
            #print (f"config logging {json.dumps(config, indent=2)}")
            logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)
            
class Resource:
    @staticmethod
    def get_resource_path(resource_name):
       # Given a string resolve it to a module relative file path unless it is already an absolute path.
        resource_path = resource_name
        if not resource_path.startswith (os.sep):
            resource_path = os.path.join (os.path.dirname (__file__), resource_path)
        return resource_path
    
    @staticmethod
    def load_json (path):
        result = None
        with open (path, 'r') as stream:
            result = json.loads (stream.read ())
        return result

    @staticmethod
    def load_yaml (path):
        result = None
        with open (path, 'r') as stream:
            result = yaml.safe_load (stream.read ())
        return result
    
    def get_resource_obj (resource_name, format=None):
        result = None
        if not format:
            if resource_name.endswith ('.yaml'):
                format = 'yaml'
            else:
                format = 'json'
        path = Resource.get_resource_path (resource_name)
        if os.path.exists (path):
            m = {
                'json' : Resource.load_json,
                'yaml' : Resource.load_yaml
            }
            if format in m:
                result = m[format](path)
        return result

    @staticmethod
    # Modified from:
    # Copyright Ferry Boender, released under the MIT license.
    def deepupdate(target, src, overwrite_keys = [], skip = []):
        """Deep update target dict with src
        For each k,v in src: if k doesn't exist in target, it is deep copied from
        src to target. Otherwise, if v is a list, target[k] is extended with
        src[k]. If v is a set, target[k] is updated with v, If v is a dict,
        recursively deep-update it.

        Updated to deal with yaml structure: if you have a list of yaml dicts,
        want to merge them by "name"

        If there are particular keys you want to overwrite instead of merge, send in overwrite_keys
        """
        if type(src) == dict:
            for k, v in src.items():
                if k in overwrite_keys:
                    target[k] = copy.deepcopy(v)
                elif type(v) == list:
                    if not k in target:
                        target[k] = copy.deepcopy(v)
                    elif type(v[0]) == dict:
                        Resource.deepupdate(target[k],v,overwrite_keys)
                    else:
                        target[k].extend(v)
                elif type(v) == dict:
                    if not k in target:
                        target[k] = copy.deepcopy(v)
                    else:
                        Resource.deepupdate(target[k], v,overwrite_keys)
                elif type(v) == set:
                    if not k in target:
                        target[k] = v.copy()
                    else:
                        target[k].update(v.copy())
                else:
                    if not k in skip:
                        target[k] = copy.copy(v)
        else:
            #src is a list of dicts, target is a list of dicts, want to merge by name (yikes)
            src_elements = { x['name']: x for x in src }
            target_elements = { x['name']: x for x in target }
            for name in src_elements:
                if name in target_elements:
                    Resource.deepupdate(target_elements[name], src_elements[name],overwrite_keys)
                else:
                    target.append( src_elements[name] )

class JSONKit:
    """ Generic kit for sql like selects on JSON object hierarchies. """
    def select (self, query, graph, field="type", target=None):
        """ Query nodes by some field, matching a list of target values """
        jsonpath_query = parse (query)
        values = [ match.value for match in jsonpath_query.find (graph) ]
        return [ val for val in values if target is None or val[field] in target ]

class Syfur:
    """
    An intentionall bad implementation of a query language reminiscent of cypher.
    Workflow's must be secure even posted from non-secure clients.
    So we prevent them from executing arbitrary cppher.
    Some of this can be achived with parameters but not all.
    Hopefully, will be replaced by a cypher parser in the future.
    In the meantime, we provide a basic graph query capability enabling automated validation and other features.

    TODO: edges.
    """
    def __init__(self):
        self.queries = {
            "match"            : "match (obj) return {field}",
            "match_type"       : "match (obj:{type}) return {field}",
            "match_params"     : "match (obj{props}) return {field}",
        }
        self.id_pat = re.compile ("^([a-zA-Z_\.0-9]+)$")
        self.value_pat = re.compile ("^([a-zA-Z_:\.0-9]+)$")
        
    def _field(self, val):
        return val if val == "*" else f"obj.{val}"
    def _gen(self, template, parameters):
        logger.debug (f"syfur template: {template}, parameters: {json.dumps(parameters, indent=2)}")
        return self.queries[template].format (**parameters)
    
    def parse (self, query):
        tokens = query.split ()
        syntax_message = "Invalid syntax. 'Query := match <filter> return <field>. Filter := arg=value. Field := <str>."
        assert len(tokens) >= 3, syntax_message
        assert tokens[0].lower() == 'match' and tokens[-2].lower() == 'return', syntax_message

        parameters = {}
        for t in tokens:
            if t == 'match':
                continue
            if t == 'return':
                break
            assert '=' in t, syntax_message
            assert not 'delete' in t and not 'detach' in t, syntax_message
            
            k, v = t.split ('=')
            assert self.id_pat.match (k).groups(), syntax_message
            assert self.value_pat.match (k).groups(), syntax_message

            parameters[k] = v

        field = self._field (tokens[-1])
        assert self.id_pat.match (field), syntax_message

        query_template = "match_params"

        props = ",".join([f"""{k}:'{v}'""" for k, v in parameters.items() ])
        parameters['props'] = f"{{ {props} }}" if len(props) > 0 else props
        parameters['field'] = field
        
        return self._gen (query_template, parameters)

class Context:
    """ A trivial context implementation. """
    def __init__(self):
        self.mem = {
        }
        self.jk = JSONKit ()
    def resolve_arg(self, val):
        return self.mem.get (val[1:], None) if val.startswith ("$") else val
    def set(self, name, val):
        self.mem[name] = val
    def select (self, key, query):
        """ context.select ('chemical_pathways', '$.knowledge_graph.nodes.[*].id,equivalent_identifiers') 
        context.select ('chemical_pathways', '$.knowledge_graph.edges.[*].type')"""
        if key in self.mem:
            return self.jk.select (query, self.mem[key])
    def top (self, type_name, k='result', n=10, start=-1):
        obj = self.mem[k] if k in self.mem else None
        result = []
        count = 0
        if obj:
            nodes = obj['knowledge_graph']['nodes']
            id2node = { n['id'] : n for n in nodes }
            edges = obj['knowledge_graph']['edges']
            sorted_edges = sorted(edges,
                                  key=lambda e: e['weight'],
                                  reverse=True)
            for e in sorted_edges:
                target = id2node [e['target_id']]
                source = id2node [e['source_id']]
                node_type = target['type']
                if node_type == type_name or (isinstance(node_type, list) and type_name in node_type):
                    count = count + 1
                    if count < start:
                        continue
                    result.append ([
                        source['name'], source['id'],
                        e['type'],
                        target['name'], target['id'],
                        round(e['weight'], 2), e['publications']
                    ])
                    if len(result) == n:
                        break
        return result
    
    def anchor (self, url, s, suffix='', delete=None):
        result = f"<a href='{url}{s}{suffix}' target='x'>{s}</a>"
        return result if delete is None else result.replace(delete,'')
    
    def toph (self, type_name, k='result', n=10, start=0):
        top = self.top (type_name, k, n, start)
        search = "https://www.google.com/search?q="
        pubmed = "https://www.ncbi.nlm.nih.gov/pubmed/?term="
        biolink_model = "https://biolink.github.io/biolink-model/docs/"
        for t in top:
            t[0] = self.anchor (search, t[0])
            t[1] = self.anchor (search, t[1])
            t[2] = self.anchor (biolink_model, t[2], suffix=".html")
            t[3] = self.anchor (search, t[3])
            t[4] = self.anchor (search, t[4])
            t[-1] = [ self.anchor (pubmed, v.replace('PMID:','')) for v in t[-1] ]
        result = '<table><tr>{}</tr></table>'.format(
            '</tr><tr>'.join(
                '<td>{}</td>'.format('</td><td>'.join(str(_) for _ in row)) for row in top)
        )
        ipd = importlib.import_module('IPython.core.display')
        ipd.display(ipd.HTML(result))
        #return result
    
class Concept:
    def __init__(self, name):
        self.name = name
        self.nodes = []
    def __repr__(self):
        return f"{self.name}:{self.nodes}"
    
class MaQ:
    def __init__(self):
        """ Extract values within parantheses someplace in a string. """
        self.paren = re.compile("^.*\(([\\\\$a-zA-Z0-9_]+)\).*$")

        """ Map a few shortcut names to common biolink model concepts. Ok, there's really just one annoying one. """
        self.shortcuts = {
            "chem" : "chemical_substance",
        }

    def question (self, nodes, edges):
        return {
            "machine_question": {
                "edges": edges,
                "nodes": nodes
            }
        }
    def edge (self, source, target, type_name=None):
        e = {
            "source_id": source,
            "target_id": target
        }
        if type_name:
            e["type_name"] = type_name
        return e
    def node (self, identifier, type_name, value=None):
        logger.debug (f"value -> {value}")
        n = {
            "id": identifier,
            "type": type_name
        }
        if value:
            n ['curie'] = value 
        return n

    def val(self, value, field="id"):
        result = value
        if isinstance(value, dict) and field in value:
            result = value[field]
        return result
    
    def parse (self, query, context):
        """ chem($drugs)->gene->disease($disease) """
        """ eventually: chem($drugs)-[$predicates]->gene->[$gd_preds]->disease($disease) """
        
        if isinstance(query, list):
            return [ question for sublist in [ self.parse (q, context) for q in query ] for question in sublist ]

        concepts = query.split ("->")
        logger.debug (f"concepts: {concepts}")
        concept_order = []
        concept_map = {}
        for index, concept in enumerate(concepts):
            if '(' in concept:
                """ This concept is parameterized. """
                name = concept.split ('(')[0]
                name = self.shortcuts.get (name, name)
                logger.debug (f"concept name concept: {concept} ===> {name}")
                concept_order.append (name)
                
                """ Match and extract the parameters. """
                val = self.paren.match (concept).groups()[0]
                value = context.resolve_arg (val)
                concept_map[name] = Concept (name)
                
                if isinstance (value,list):
                    """ It's a list. Build the set and permute. """
                    concept_map[name].nodes = [ self.node (
                        identifier = index,
                        type_name = name,
                        value = self.val(v)) for v in value ]
                elif isinstance (value, str):
                    concept_map[name].nodes = [ self.node (
                        identifier = index,
                        type_name = name,
                        value = self.val(value)) ]
            else:
                name = self.shortcuts.get (concept, concept)
                concept_order.append (name)
                concept_map[name] = Concept (name)
                concept_map[name].nodes = [ self.node (
                    identifier = index,
                    type_name = name) ]
            
        edges = []
        questions = []
        for index, name in enumerate (concept_order):
            concept = concept_map [name]
            logger.debug (f"concept: {concept}")
            previous = concept_order[index-1] if index > 0 else None
            if index == 0:
                for node in concept.nodes:
                    """ Model the first step. """
                    questions.append (self.question (
                        nodes = [ node ],
                        edges = []))
            else:
                new_questions = []
                for question in questions:
                    logger.debug (f"question: {question}")
                    for node in concept.nodes:
                        """ Permute each question. """
                        nodes = copy.deepcopy (question["machine_question"]['nodes'])
                        lastnode = nodes[-1]
                        nodes.append (node)
                        edges = copy.deepcopy (question["machine_question"]['edges'])
                        edges.append (self.edge (
                            source=lastnode['id'],
                            target=node['id']))
                        new_questions.append (self.question (
                            nodes = nodes,
                            edges = edges))
                        #logger.debug (f"-------------------------------------------------")
                        #logger.debug (f"new_questions: {json.dumps(new_questions, indent=2)}")
                questions = new_questions

        return questions
                
                
if __name__ == '__main__':
    m = MaQ ()
    c = Context ()
    m.parse ("""chem($drugs)->gene->disease($disease) """, c)
    
