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
from collections import Iterable
from collections import namedtuple
from tranql.disease_vocab import DiseaseVocab
from jinja2 import Template
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


    @staticmethod
    def setup_logging ():
        logging_config_path = os.path.join(os.path.dirname(__file__), 'logging.yaml')
        with open(logging_config_path, 'rt') as f:
            logging_config = yaml.safe_load(f.read())
            #    print (json.dumps(logging_config, indent=2))
            logging.config.dictConfig(logging_config)

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

class Context:
    """ A trivial context implementation. """
    def __init__(self):
        self.mem = {
        }
        self.jk = JSONKit ()
        generate_gene_vocab (self)
        #generate_disease_vocab (self)
        DiseaseVocab (self)

    '''
    def resolve_arg(self, val):
        return self.mem.get (val[1:], None) if val.startswith ("$") else val
    '''
    def resolve_arg(self, val):
        if isinstance(val, str):
            return self.mem.get (val[1:], None) if val.startswith ("$") else val
        else:
            return val

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
    def __init__(self, name, type_name, include_patterns = [], exclude_patterns = []):
        self.name = name
        self.type_name = type_name
        self.nodes = []
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
    def __repr__(self):
        return f"{self.name}:{self.nodes}"
    def set_exclude_patterns (self, patterns):
        self.exclude_patterns = patterns
    def filter_nodes (self, nodes):
        final_list = []
        for n in nodes:
            exclude = False
            for pat in self.exclude_patterns:
                identifier = n if isinstance(n, str) else (n['curie'] if 'curie' in n else n['id'])
                matches = re.search (pat, identifier, re.IGNORECASE)
                if matches is not None:
                    exclude = True
                    break
            include = not len(self.include_patterns) > 0
            for pat in self.include_patterns:
                identifier = n if isinstance(n, str) else (n['curie'] if 'curie' in n else n['id'])
                matches = re.search (pat, identifier, re.IGNORECASE)
                if matches is not None:
                    include = True
                    break
            if include and not exclude:
                final_list.append (n)
        return final_list
    def set_nodes (self, nodes):
        keep_nodes = {}
        for n in nodes:
            identifier = n if isinstance(n, str) else (n['curie'] if 'curie' in n else n['id'])
            keep_nodes[identifier] = n
        self.nodes = self.filter_nodes (list(keep_nodes.values()))
    def apply_filters (self):
        nodes = self.filter_nodes (self.nodes)
        self.nodes = nodes

class Text:
    """ Utilities for processing text. """

    @staticmethod
    def get_curie (text):
        return text.upper().split(':', 1)[0] if ':' in text else None

    @staticmethod
    def un_curie (text):
        return text.split (':', 1)[1] if ':' in text else text

    @staticmethod
    def short (obj, limit=80):
        text = str(obj) if obj else None
        return (text[:min(len(text),limit)] + ('...' if len(text)>limit else '')) if text else None

def generate_gene_vocab ():
    gene_map = {}
    with open('genes.txt', 'r') as stream:
        for line in stream:
            parts = line.split ('\t')
            identifier = parts[0]
            symbol = parts[1]

            symbol = symbol.replace ('@', '_')
            symbol = symbol.replace ('-', '_')
            if not "~withdrawn" in symbol and not ' ' in symbol:
                gene_map[symbol] = identifier

def generate_gene_vocab (context):
    file_name = os.path.join (os.path.dirname (__file__), "conf", "genes.txt")
    with open(file_name, 'r') as stream:
        for line in stream:
            parts = line.split ('\t')
            identifier = parts[0]
            symbol = parts[1]
            symbol = symbol.replace ('@', '_')
            symbol = symbol.replace ('-', '_')
            if not "~withdrawn" in symbol and not ' ' in symbol:
                context.set(symbol, identifier)

def generate_disease_vocab (context):
    file_name = os.path.join (os.path.dirname (__file__), "conf", "mondo.json")
    with open(file_name, "r") as stream:
        ontology = json.load (stream)
        for graph in ontology['graphs']:
            for node in graph['nodes']:
                label = node['lbl'].\
                        replace (' ', '_').\
                        replace (',', '').\
                        replace ('-','_') if 'lbl' in node else None
                if label:
                    identifier = node['id'].\
                                 split ('/')[-1].\
                                 replace ('_', ':')
                    #print (f"{label}={identifier}")
                    context.set (label, identifier)
        template = Template ("""
class DiseaseVocab:
   def __init__(self, context):
       context.mem.update ({
           {% for k, v in disease_map.items () %}
           "{{ k.lower() }}" : "{{ v }}"{{ "," if not loop.last }}{% endfor %}
       })""")
        text = template.render (disease_map=context.mem)
        with open("disease_vocab.py", "w") as stream:
            stream.write (text)

# Flatten a list of generic type
# source: https://stackoverflow.com/a/2158532
def flatten(l):
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el

#{% if i < len(list(disease_map.items ())) %},{%
def light_merge(source, destination, no_list_repeat=True):
    for key, value in source.items():
        if isinstance(value, list) and key in destination:
            try:
                destination[key] = destination[key] + value
                if no_list_repeat:
                    destination[key] = list(set(destination[key]))
            except:
                pass
        else:
            destination[key] = value

    return destination
def deep_merge(source, destination, no_list_repeat=True):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge(value, node, no_list_repeat)
        elif isinstance(value, list) and key in destination:
            try:
                destination[key] = destination[key] + value
                if no_list_repeat:
                    destination[key] = list(set(destination[key]))
            except:
                pass
        else:
            destination[key] = value

    return destination

if __name__ == '__main__':
    #generate_gene_vocab ()
    generate_disease_vocab (Context ())
