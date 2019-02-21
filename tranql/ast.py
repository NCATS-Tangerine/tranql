import copy
import json
import logging
import requests
import requests_cache
import sys
import traceback
from tranql.util import Concept
from tranql.util import JSONKit

logger = logging.getLogger (__name__)

class Bionames:
    """ Resolve natural language names to ontology identifiers. """
    def __init__(self):
        """ Initialize the operator. """
        self.url = "https://bionames.renci.org/lookup/{input}/{type}/"
    
    def get_ids (self, name, type_name):
        url = self.url.format (**{
            "input" : name,
            "type"  : type_name
        })
        result = None
        response = requests.get(
            url = url,
            headers = {
                'accept': 'application/json'
            })
        if response.status_code == 200 or response.status_code == 202:
            result = response.json ()
        else:
            raise ValueError (response.text)
        return result
    
class Statement:
    """ The interface contract for a statement. """
    def execute (self, interpreter, context={}):
        pass

    def resolve_backplane_url(self, url, interpreter):
        result = url
        if url.startswith ('/'):
            backplane = interpreter.context.resolve_arg ("$backplane")
            result =  f"{backplane}{url}"
        return result    

    def message (self, q_nodes=[], q_edges=[], k_nodes=[], k_edges=[], options={}):
        """ Generate the frame of a question. """
        return {
            "question_graph": {
                "edges": q_edges,
                "nodes": q_nodes
            },
            "knowledge_graph" : {
                "nodes" : k_nodes,
                "edges" : k_edges
            },
            "knowledge_maps" : [
                {}
            ],
            "options" : options
        }
    
    def request (self, url, message):
        """ Make a web request to a service (url) posting a message. """
        logger.debug (f"request> {json.dumps(message, indent=2)}")
        response = {}
        try:
            http_response = requests.post (
                url = url,
                json = message,
                headers = {
                    'accept': 'application/json'
                })
            """ Check status and handle response. """
            if http_response.status_code == 200 or http_response.status_code == 202:
                response = http_response.json ()
                logging.debug (f"{json.dumps(response, indent=2)}")
            else:
                logger.error (f"error {http_response.status_code} processing request: {message}")
                logger.error (http_response.text)
        except:
            logger.error (f"error performing request: {json.dumps(message, indent=2)} to url: {url}")
            traceback.print_exc ()
        return response
    
class SetStatement(Statement):
    """ Model the set statement's semantics and variants. """
    def __init__(self, variable, value=None, jsonpath_query=None):
        """ Model the various forms of assignment supported. """
        self.variable = variable
        self.value = value
        self.jsonpath_query = jsonpath_query
        self.jsonkit = JSONKit ()
    def execute (self, interpreter, context={}):
        logger.debug (f"set-statement: {self.variable}={self.value}")
        if self.value:
            logger.debug (f"exec-set-statement(explicit-value): {self}")
            interpreter.context.set (self.variable, self.value)
        elif 'result' in context:
            result = context['result']
            if self.jsonpath_query is not None:
                logger.debug (f"exec-set-statement(jsonpath): {self}")
                value = self.jsonkit.select (
                    query=self.jsonpath_query,
                    graph=result)
                interpreter.context.set (
                    self.variable,
                    value)
            else:
                logger.debug (f"exec-set-statement(result): {self}")
                interpreter.context.set (self.variable, result)

    def __repr__(self):
        result = f"SET {self.variable}"
        if self.jsonpath_query is not None:
            result = f"SET {self.jsonpath_query} AS {self.variable}"
        elif self.value is not None:
            result = f"{result} = {self.value}"
        return result

class CreateGraphStatement(Statement):
    """ Create a graph, sending it to a sink. """
    def __init__(self, graph, service, name):
        """ Construct a graph creation statement. """
        self.graph = graph
        self.service = service
        self.name = name
    def __repr__(self):
        return f"CREATE GRAPH {self.graph} AT {self.service} AS {self.name}"
    def execute (self, interpreter):
        """ Execute the statement. """
        self.service = self.resolve_backplane_url(self.service,
                                                  interpreter)
        graph = interpreter.context.resolve_arg (self.graph)
        logger.debug (f"------- {type(graph).__name__}")
        logger.debug (f"--- create graph {self.service} at {json.dumps(graph, indent=2)}")
        logger.debug (f"--- create graph {self.service} graph-> {json.dumps(graph, indent=2)}")
        '''
        message = self.message (
            k_nodes = graph['knowledge_graph']['nodes'],
            k_edges = graph['knowledge_graph']['edges'],
            options = { "name" : self.name })
        '''
        response = None
        #with requests_cache.disabled ():
        response = self.request (url=self.service,
                                 message=graph)
        interpreter.context.set (self.name, response)
        
class SelectStatement(Statement):
    """
    Model a select statement.
    This entails all capabilities from specifying a knowledge path, service to invoke, constraints, and handoff.
    """
    def __init__(self):
        """ Initialize a new select statement. """
        #self.concept_order = []
        #self.concepts = {}
        self.query = Query ()
        self.service = None
        self.where = []
        self.set_statements = []
        self.id_count = 0

    def __repr__(self):
        #return f"SELECT {self.concepts} from:{self.service} where:{self.where} set:{self.set_statements}"
        return f"SELECT {self.query} from:{self.service} where:{self.where} set:{self.set_statements}"
    
    def next_id(self):
        self.id_count += 1
        return self.id_count
    def edge (self, source, target, type_name=None):
        """ Generate a question edge. """
        e = {
            "id" : f"e{self.next_id()}",
            "source_id": source,
            "target_id": target
        }
        if type_name:
            e["type_name"] = type_name
        return e
    def node (self, identifier, type_name, value=None):
        """ Generate a question node. """
        if identifier is None:
            identifier = self.next_id ()
        n = {
            "id": f"n{identifier}",
            "type": type_name
        }
        if value:
            n ['curie'] = value 
        return n

    def val(self, value, field="id"):
        """ Get the value of an object. """
        result = value
        if isinstance(value, dict) and field in value:
            result = value[field]
        return result
    def expand_nodes (self, interpreter, concept):
        """ Expand variable expressions to nodes. """
        value = concept.nodes[0] if len(concept.nodes) > 0 else None
        if value and isinstance(value, str) and value.startswith ("$"):
            varname = value
            value = interpreter.context.resolve_arg (varname)
            logger.debug (f"resolved {varname} to {value}")
            if value == None:
                raise ValueError (f"Undefined variable: {varname}")
            if isinstance(value, list):
                concept.nodes = value
            elif isinstance(value, str):
                if not ':' in value:
                    logger.debug (f"no ':' in {value} concept:{concept}")
                    bionames = Bionames ()
                    response = bionames.get_ids (value, concept.name)
                    logger.debug (f"fetching ids for [{value}] from bionames.")
                    concept.nodes = response
                else:
                    concept.nodes = [ self.node (
                        identifier = None,
                        value=value,
                        type_name = concept.name) ]
            else:
                logger.debug (f"value: {value}")
                raise ValueError (f"Invalid type {type(value)} interpolated.")

    def generate_questions (self, interpreter):
        """
        Given an archetype question graph and values, generate question
        instances for each value permutation.
        """
        for index, name in enumerate(self.query.order):
            concept = self.query[name]
            if len(concept.nodes) > 0:
                self.expand_nodes (interpreter, concept)
                logger.debug (f"concept--nodes: {concept.nodes}")
                for value in concept.nodes:
                    logger.debug (f"concept-nodes: index:{index} type:{name} concept:{concept}")
                    if isinstance (value, list):
                        """ It's a list of values. Build the set preparing to permute. """
                        concept.nodes = [ self.node (
                            identifier = index,
                            type_name = concept.name,
                            value = self.val(v)) for v in value ]
                    elif isinstance (value, str):
                        """ It's a single value. """
                        concept.nodes = [ self.node (
                            identifier = index,
                            type_name = concept.name,
                            value = self.val(value)) ]
            else:
                """ There are no values - it's just a template for a model type. """
                concept.nodes = [ self.node (
                    identifier = index,
                    type_name = concept.name) ]
        options = {}
        for constraint in self.where:
            logger.debug (f"manage constraint: {constraint}")
            name, op, value = constraint
            value = interpreter.context.resolve_arg (value)
            if not name in self.query:
                """
                This is not constraining a concept name in the graph query.
                So interpret it as an option to the underlying service.
                """
                options[name] = constraint[1:]
        edges = []
        questions = []
        logger.debug (f"concept order> {self.query.order}")
        for index, name in enumerate (self.query.order):
            concept = self.query[name] 
            previous = self.query.order[index-1] if index > 0 else None
            logger.debug (f"query:{self.query}")
            logger.debug (f"questions:{index} ==>> {json.dumps(questions, indent=2)}")
            if index == 0:
                """ Model the first step. """
                if len(concept.nodes) > 0:
                    """ The first concept is bound. """
                    for node in concept.nodes:
                        questions.append (self.message (
                            q_nodes = [ node ],
                            q_edges = [],
                            options = options))
                else:
                    """ No nodes specified for the first concept. """
                    questions.append (self.message (options))
            else:
                """ Not the first concept - permute relative to previous. """
                new_questions = []
                for question in questions:
                    if len(concept.nodes) > 0:
                        for node in concept.nodes:
                            """ Permute each question. """
                            nodes = copy.deepcopy (question["question_graph"]['nodes'])
                            lastnode = nodes[-1]
                            nodes.append (node)
                            edges = copy.deepcopy (question["question_graph"]['edges'])
                            edges.append (self.edge (
                                source=lastnode['id'],
                                target=node['id']))
                            new_questions.append (self.message (
                                q_nodes = nodes,
                                options = options,
                                q_edges = edges))
                    else:
                        next_id = len(question['question_graph']['nodes'])
                        question['question_graph']['nodes'].append (
                            self.node (identifier = str(next_id),
                                       type_name = concept.name))
                        question['question_graph']['edges'].append (
                            self.edge (
                                source = question['question_graph']['nodes'][-2]['id'],
                                target = f"n{str(next_id)}"))
                        next_id += 1
                        new_questions.append (self.message (options))
                questions = new_questions
        return questions

    def execute (self, interpreter, context={}):
        """
        Execute all statements in the abstract syntax tree.
        - Generate questions by permuting bound values.
        - Resolve the service name.
        - Execute the questions.
        """
        self.service = self.resolve_backplane_url (self.service, interpreter)
        questions = self.generate_questions (interpreter)
        if len(questions) == 0:
            raise ValueError ("No questions generated")
        service = interpreter.context.resolve_arg (self.service)
        responses = [ self.request (service, q) for q in questions ]
        if len(responses) == 0:
            raise ValueError ("No responses received")
        elif len(responses) == 1:
            result = responses[0]
        elif len(responses) > 1:
            # TODO - this isn't the right logic. Revisit merging nodes, edges, etc.
            result = responses[0]
            nodes = result['knowledge_graph']['nodes']
            edges = result['knowledge_graph']['edges']
            nodes = { n['id'] : n for n in nodes }
            for response in responses[1:]:
                other_nodes = response['knowledge_graph']['nodes']
                other_edges = response['knowledge_graph']['edges']
                for n in other_nodes:
                    nodes[n['id']] = n
                edges += other_edges
            result['knowledge_graph']['nodes'] = nodes.values ()
        for set_statement in self.set_statements:
            logger.debug (f"{set_statement}")
            set_statement.execute (interpreter, context = { "result" : result })
        return result
    
class TranQL_AST:
    """Represent the abstract syntax tree representing the logical structure of a parsed program."""
    def __init__(self, parse_tree):
        """ Create an abstract syntax tree from the parser token stream. """
        self.statements = []
        self.parse_tree = parse_tree
        logger.debug (f"{json.dumps(self.parse_tree, indent=2)}")
        for index, element in enumerate(self.parse_tree):
            if isinstance (element, list):
                statement = self.remove_whitespace (element, also=["->"])
                if element[0] == 'set':
                    if len(element) == 4:
                        self.statements.append (SetStatement (
                            variable = element[1],
                            value = element[3]))
                elif isinstance(element[0], list):
                    statement = self.remove_whitespace (element[0], also=["->"])
                    command = statement[0]
                    if command == 'select':
                        self.parse_select (element)
                    elif command == 'create':
                        self.parse_create (element)

    def parse_create(self, element):
        """ Parse a create graph statement. """
        element = self.remove_whitespace (element)
        self.statements.append (
            CreateGraphStatement (
                graph = element[0][2],
                service = element[1][1],
                name = element[2][1]))
        logger.debug (f"--parse_create(): {self.statements[-1]}")
        
    def remove_whitespace (self, group, also=[]):
        """
        Delete spurious items in a statement.
        TODO: Look at enhancing the parser to provider cleaner input in the first place.
        """
        return [ x for x in group
                 if not isinstance(x, str) or
                 (not x.isspace () and not x in also) ]
        
    def parse_select (self, statement):
        """ Parse a select statement. """
        select = SelectStatement ()
        for e in statement:
            if self.is_command (e):
                e = self.remove_whitespace (e, also=["->"])
                command = e[0]
                if command == 'select':
                    for token in e[1:]:
                        select.query.add (token)
                if command == 'from':
                    select.service = e[1][0]
                elif command == 'where':
                    for condition in e[1:]:
                        if isinstance(condition, list) and len(condition) == 3:
                            select.where.append (condition)
                            var, op, val = condition
                            if var in select.query and op == '=':
                                select.query[var].nodes.append (val)
                            else:
                                select.where.append ([ var, op, val ])
                elif command == 'set':
                    element = e[1]
                    if len(element) == 3:
                        select.set_statements.append (
                            SetStatement (variable=element[2],
                                          value=None,
                                          jsonpath_query=element[0]))
                    elif len(element) == 1:
                        select.set_statements.append (
                            SetStatement (variable=element[0]))
        self.statements.append (select)

    def is_command (self, e):
        """ Is this structured like a command? """
        return isinstance(e, list) and len(e) > 0
    
    def __repr__(self):
        return json.dumps(self.parse_tree)

class Query:
    """ Model a query. 
    TODO:
       - Model queries with arrows in both diretions.
       - Model predicates
       - Model arbitrary shaped graphs.
    """
    def __init__(self):
        self.order = []
        self.concepts = {}
    def add(self, key):
        concept = key
        name = key
        if ':' in key:
            if key.count (':') > 1:
                raise ValueError (f"Illegal concept id: {key}")
            name, concept = key.split (':')
        self.order.append (name)
        self.concepts[name] = Concept (concept)
    def __getitem__(self, key):
        return self.concepts [key]
    def __setitem__(self, key, value):
        raise ValueError ("Not implemented")
    def __delitem__ (self, key):
        del self.concepts[key]
    def __contains__ (self, key):
        return key in self.concepts
    def __repr__(self):
        return str(self.concepts)
