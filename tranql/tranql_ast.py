import copy
import json
import logging
import requests
import requests_cache
import sys
import traceback
import time # Basic time profiling for async
from collections import defaultdict
from tranql.concept import ConceptModel
from tranql.concept import BiolinkModelWalker
from tranql.tranql_schema import Schema
from tranql.util import Concept
from tranql.util import JSONKit
from tranql.request_util import async_make_requests
from tranql.util import Text
from tranql.tranql_schema import Schema
from tranql.exception import ServiceInvocationError
from tranql.exception import UndefinedVariableError
from tranql.exception import UnableToGenerateQuestionError
from tranql.exception import MalformedResponseError
from tranql.exception import IllegalConceptIdentifierError
from tranql.exception import UnknownServiceError

logger = logging.getLogger (__name__)

def truncate (s, max_length=75):
    return (s[:max_length] + '..') if len(s) > max_length else s

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
            raise ServiceInvocationError (response.text)
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
        logger.debug (f"request({url})> {json.dumps(message, indent=2)}")
        response = {}
        unknown_service = False
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
                #logger.error (f" response: {json.dumps(response, indent=2)}")
                status = response.get('status', None)
                if status == "error":
                    raise ServiceInvocationError(
                        message=f"An error occurred invoking service: {url}.",
                        details=truncate(response['message'], max_length=5000))
                logging.debug (f"{json.dumps(response, indent=2)}")
            elif http_response.status_code == 404:
                unknown_service = True
            else:
                logger.error (f"error {http_response.status_code} processing request: {message}")
                logger.error (http_response.text)
        except ServiceInvocationError as e:
            raise e
        except Exception as e:
            logger.error (f"error performing request: {json.dumps(message, indent=2)} to url: {url}")
            #traceback.print_exc ()
            logger.error (traceback.format_exc ())
        if unknown_service:
            raise UnknownServiceError (f"Service {url} was not found. Is it misspelled?")
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
        return_val = None
        if self.value:
            logger.debug (f"exec-set-statement(explicit-value): {self}")
            interpreter.context.set (self.variable, self.value)
            return_val = self.value
        elif 'result' in context:
            result = context['result']
            if self.jsonpath_query is not None:
                logger.debug (f"exec-set-statement(jsonpath): {self}")
                value = self.jsonkit.select (
                    query=self.jsonpath_query,
                    graph=result)
                if len(value) == 0:
                    logger.warn (f"Got empty set for query {self.jsonpath_query} on " +
                           f"object {json.dumps(result, indent=2)}")
                interpreter.context.set (
                    self.variable,
                    value)
                return_val = value
            else:
                logger.debug (f"exec-set-statement(result): {self}")
                interpreter.context.set (self.variable, result)
                return_val = result
        return return_val

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
        logger.debug (f"--- create graph {self.service} graph-> {json.dumps(graph, indent=2)}")
        response = None
        with requests_cache.disabled ():
            response = self.request (url=self.service,
                                     message=graph)
        interpreter.context.set (self.name, response)
        return response

def synonymize(nodetype,identifier):
    robokop_server = 'robokopdb2.renci.org'
    robokop_server = 'robokop.renci.org'
    url=f'http://{robokop_server}/api/synonymize/{identifier}/{nodetype}/'
    url=f'http://{robokop_server}:6010/api/synonymize/{identifier}/{nodetype}/'
    response = requests.post(url)
    logger.debug (f'Return Status: {response.status_code}' )
    if response.status_code == 200:
        return response.json()
    return []

class SelectStatement(Statement):
    """
    Model a select statement.
    This entails all capabilities from specifying a knowledge path, service to invoke, constraints, and handoff.
    """
    def __init__(self, ast, service=None):
        """ Initialize a new select statement. """
        self.ast = ast
        self.query = Query ()
        self.service = service
        self.where = []
        self.set_statements = []
        self.jsonkit = JSONKit ()
        self.planner = QueryPlanStrategy (ast.backplane)

    def __repr__(self):
        return f"SELECT {self.query} from:{self.service} where:{self.where} set:{self.set_statements}"

    def edge (self, index, source, target, type_name=None):
        """ Generate a question edge. """
        e = {
            "id" : f"e{index}",
            "source_id": source,
            "target_id": target
        }
        if type_name is not None:
            e["type"] = type_name
        return e
    def node (self, index, type_name, value=None):
        """ Generate a question node. """
        n = {
            "id": f"{index}",
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

    def resolve_name (self, name, type_name):
        bionames = Bionames ()
        result = [ r['id'] for r in bionames.get_ids (name, type_name) ]
        #result += self.synonymize (value, type_name)
        if type_name == 'chemical_substance':
            response = requests.get (f"http://mychem.info/v1/query?q={name}").json ()
            for obj in response['hits']:
                if 'chebi' in obj:
                    result.append (obj['chebi']['id'])
        logger.debug (f"name resolution result: {name} => {result}")
        return result

    def expand_nodes (self, interpreter, concept):
        """ Expand variable expressions to nodes. """
        value = concept.nodes[0] if len(concept.nodes) > 0 else None
        if value and isinstance(value, str):
            if value.startswith ("$"):
                varname = value
                value = interpreter.context.resolve_arg (varname)
                logger.debug (f"resolved {varname} to {value}")
                if value == None:
                    raise UndefinedVariableError (f"Undefined variable: {varname}")
                elif isinstance (value, str):
                    concept.set_nodes ([ value ])
                elif isinstance(value, list):
                    """ Binding multiple values to a node. """
                    concept.set_nodes (value)
                else:
                    raise TranQLException (
                        f"Internal failure: object of unhandled type {type(value)}.")
            else:
                """ Bind a single value to a node. """
                if not ':' in value:
                    """ Deprecated. """
                    """ Bind something that's not a curie. Dynamic id lookup.
                    This is frowned upon. While it *may* be useful for prototyping and,
                    interactive exploration, it will probably be removed. """
                    logger.debug (f"performing dynamic lookup resolving {concept}={value}")
                    concept.set_nodes (self.resolve_name (value, concept.type_name))
                    logger.debug (f"resolved {value} to identifiers: {concept.nodes}")
                else:
                    """ This is a single curie. Bind it to the node. """
                    pass

    def plan (self, plan):
        """ Plan a query that may span reasoners. This uses a configured schema to determine
        what kinds of queries each reasoner can respond to. """
        statements = []
        for phase in plan:
            schema, url, steps = phase
            """ Make a new select statement for each segment. Set the from clause given the url. """
            logger.debug (f"Making select for schema segment: {schema}")
            statement = SelectStatement (ast=self.ast, service=url)
            statements.append (statement)
            for index, step in enumerate (steps):
                subj, pred, obj = step
                logger.debug (f" --> {schema}:{url} {subj} {pred} {obj}")
                """ Add each concept and transition to the query. """
                statement.query.add (subj)
                statement.query.add (pred)
                if index == len(steps) - 1:
                    """ If this is the last concept, add the object as well. """
                    statement.query.add (obj)
                for constraint in self.where:
                    """ Add constraints, if they apply to this schema. """
                    name, op, val = constraint
                    prefix = f"{schema}."
                    if name.startswith (prefix):
                        """ Remove the schema prefix as we add the constraint. """
                        constraint_copy = copy.deepcopy (constraint)
                        constraint_copy[0] = name.replace (prefix, "")
                        statement.where.append (constraint_copy)
        self.query.disable = True # = Query ()
        return statements

    def generate_questions (self, interpreter):
        """
        Given an archetype question graph and values, generate question
        instances for each value permutation.
        """
        for index, name in enumerate(self.query.order):
            """ Convert literals into nodes in the message's question graph. """
            concept = self.query[name]
            if len(concept.nodes) > 0:
                self.expand_nodes (interpreter, concept)
                logger.debug (f"concept--nodes: {concept.nodes}")
                concept.set_nodes ([
                    self.node (
                        index = name, #index,
                        type_name = concept.type_name,
                        value = self.val(v, field='curie'))
                    for v in concept.nodes
                ])
                filters = interpreter.context.resolve_arg ('$id_filters')
                if filters:
                    filters = [ f.lower () for f in filters.split(",") ]
                    concept.set_nodes ([
                        n for n in concept.nodes
                        if not n['curie'].split(':')[0].lower () in filters
                    ])
            else:
                """ There are no values - it's just a template for a model type. """
                concept.set_nodes ([ self.node (
                    index = name, #index,
                    type_name = concept.type_name) ])

        options = {}
        for constraint in self.where:
            """ This is where we pass constraints to a service. We do this only for constraints
            which do not refer to elements in the query. """
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
            #logger.debug (f"questions:{index} ==>> {json.dumps(questions, indent=2)}")
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
                            if len(nodes) == 0:
                                logger.debug (f"No values in concept {concept.name}")
                                continue
                            lastnode = nodes[-1]
                            nodes.append (node)
                            edges = copy.deepcopy (question["question_graph"]['edges'])
                            edge_spec = self.query.arrows[index-1]
                            if edge_spec.direction == self.query.forward_arrow:
                                edges.append (self.edge (
                                    index = index,
                                    source=lastnode['id'],
                                    target=node['id'],
                                    type_name = edge_spec.predicate))
                            else:
                                edges.append (self.edge (
                                    index = index,
                                    source=node['id'],
                                    target=lastnode['id'],
                                    type_name = edge_spec.predicate))
                            new_questions.append (self.message (
                                q_nodes = nodes,
                                options = options,
                                q_edges = edges))
                    else:
                        query_nodes = question['question_graph']['nodes']
                        question['question_graph']['nodes'].append (
                            self.node (index = name, #index,
                                       type_name = concept.type_name))
                        source_id = query_nodes[-2]['id']
                        target_id = query_nodes[-1]['id']
                        question['question_graph']['edges'].append (
                            self.edge (
                                index = index,
                                source = source_id,
                                target = target_id))
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
        result = None
        if self.service == "/schema":
            result = self.execute_plan (interpreter)
        else:
            self.service = self.resolve_backplane_url (self.service, interpreter)
            questions = self.generate_questions (interpreter)
            service = interpreter.context.resolve_arg (self.service)

            """ Invoke the service and store the response. """

            """
            Basic data from default query about asthma (in seconds):
                Async (4 parallel requests at once):
                    [
                        8.950051546096802,
                        8.789488792419434,
                        8.992945432662964
                    ]
                    Average time: 8.910828590393066

                Serial:
                    [
                        120.87169480323792,
                        121.13019347190857,
                        120.94755744934082
                    ]
                    Average time: 120.9831485748291

                Average speed increase of async requests: 1357% (almost 13.6 times faster)
            """


            # For each question, make a request to the service with the question
            # Only have a maximum of maximumParallelRequests requests executing at any given time
            # logger.setLevel (logging.DEBUG)
            logger.debug (f"Starting queries on service: {service} (asynchronous={interpreter.asynchronous})")
            # logger.setLevel (logging.INFO)
            prev = time.time ()
            # We don't want to flood the service so we cap the maximum number of requests we can make to it.
            maximumQueryRequests = 50
            if interpreter.asynchronous:
                maximumParallelRequests = 4
                responses = async_make_requests ([
                    {
                        "method" : "post",
                        "url" : service,
                        "json" : q,
                        "headers" : {
                            "accept": "application/json"
                        },
                        "timeout" : 22
                    }
                    for q in questions[:maximumQueryRequests]
                ],maximumParallelRequests)
                errors = responses["errors"]
                responses = responses["responses"]
                if len(errors) > 0:
                    interpreter.context.set('requestErrors', errors)

            else:
                responses = []
                for index, q in enumerate(questions):
                    logger.debug (f"executing question {json.dumps(q, indent=2)}")
                    response = self.request (service, q)
                    # TODO - add a parameter to limit service invocations.
                    # Until we parallelize requests, cap the max number we attempt for performance reasons.
                    if index >= maximumQueryRequests:
                        break
                    #logger.debug (f"response: {json.dumps(response, indent=2)}")
                    responses.append (response)

            if len(responses) == 0:
                raise ServiceInvocationError (
                    f"No valid results from service {self.service} executing " +
                    f"query {self.query}. Unable to continue query. Exiting.")
                #raise ServiceInvocationError (f"No responses received from {service}")

            # logger.setLevel (logging.DEBUG)
            logger.debug (f"Making requests took {time.time()-prev} s (asynchronous = {interpreter.asynchronous})")
            # logger.setLevel (logging.INFO)

            result = self.merge_results (responses, service)
        interpreter.context.set('result', result)
        """ Execute set statements associated with this statement. """
        for set_statement in self.set_statements:
            logger.debug (f"{set_statement}")
            set_statement.execute (interpreter, context = { "result" : result })
        return result

    def execute_plan (self, interpreter):
        """ Execute a query using a schema based query planning strategy. """
        self.service = ''
        plan = self.planner.plan (self.query)
        statements = self.plan (plan)
        responses = []
        for index, statement in enumerate(statements):
            logger.debug (f" -- {statement.query}")
            response = statement.execute (interpreter)
            responses.append (response)
            if index < len(statements) - 1:
                """ Implement handoff. Finds the type name of the first element of the
                next plan segment, looks up values for that type from the answer bindings of the
                last response, and transfers values to the new question. TODO: incorporate
                user specified namnes. """
                next_statement = statements[index+1]
                name = next_statement.query.order [0]
                #name = statement.query.order[-1]
                #values = self.jsonkit.select (f"$.knowledge_map.[*].node_bindings.{name}", response)
                logger.error (f"querying $.knowledge_map.[*].[*].node_bindings.{name} from {json.dumps(response, indent=2)}")
                values = self.jsonkit.select (f"$.knowledge_map.[*].[*].node_bindings.{name}", response)
                first_concept = next_statement.query.concepts[name]
                first_concept.set_nodes (values)
                if len(values) == 0:
                    message = f"No valid results from service {statement.service} executing " + \
                              f"query {statement.query}. Unable to continue query. Exiting."
                    raise ServiceInvocationError (
                        message = message,
                        details = Text.short (obj=f"{json.dumps(response, indent=2)}", limit=1000))
                print (f"{values}")
        merged = self.merge_results (responses, self.service)
        questions = self.generate_questions (interpreter)
        merged['question_graph'] = questions[0]['question_graph']
        return merged

    def merge_results (self, responses, service):
        """ Merge results. """
        result = responses[0] if len(responses) > 0 else None
        if not 'knowledge_graph' in result:
            message = "Malformed response does not contain knowledge_graph element."
            logger.error (f"{message} svce: {service}: {json.dumps(result, indent=2)}")
            raise MalformedResponseError (message)
        kg = result['knowledge_graph']
        #answers = result['answers']
        answers = result['knowledge_map']

        node_map = { n['id'] : n for n in kg.get('nodes',[]) }
        for response in responses[1:]:
            #logger.error (f"   -- Response message: {json.dumps(result, indent=2)}")
            # TODO: Preserve reasoner provenance. This treats nodes as equal if
            # their ids are equal. Consider merging provenance/properties.
            # Edges, we may keep distinct and whole or merge to some tbd extent.
            if 'knowledge_graph' in response:
                rkg = response['knowledge_graph']
                kg['edges'] += rkg['edges'] if 'edges' in rkg else []
                #result['answers'] += response['answers']
                result['knowledge_map'] += response['knowledge_map']
                other_nodes = rkg['nodes'] if 'nodes' in rkg else []
                for n in other_nodes:
                    if not n['id'] in node_map:
                        node_map[n['id']] = n
                        kg['nodes'].append (n)
        return result

class TranQL_AST:
    """Represent the abstract syntax tree representing the logical structure of a parsed program."""

    def __init__(self, parse_tree, backplane):
        logger.debug (f"{json.dumps(parse_tree, indent=2)}")
        """ Create an abstract syntax tree from the parser token stream. """
        self.schema = Schema (backplane=backplane)
        self.backplane = backplane
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
        select = SelectStatement (ast=self)
        for e in statement:
            if self.is_command (e):
                e = self.remove_whitespace (e)
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
                            if var in select.query:
                                if op == '=':
                                    select.query[var].set_nodes ([ val ])
                                elif op == '=~':
                                    select.query[var].include_patterns.append (val)
                                elif op == '!=~':
                                    select.query[var].exclude_patterns.append (val)
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

class Edge:
    def __init__(self, direction, predicate=None):
        self.direction = direction
        self.predicate = predicate
    def __repr__(self):
        return f"edge[dir:{self.direction},pred:{self.predicate}]"

class Query:
    """ Model a query.
    TODO:
       - Model queries with arrows in both diretions.
       - Model predicates
       - Model arbitrary shaped graphs.
    """

    """ Arrows in the query. """
    back_arrow = "<-"
    forward_arrow = "->"

    """ The biolink model. Will use for query validation. """
    concept_model = ConceptModel ("biolink-model")

    def __init__(self):
        self.order = []
        self.arrows = []
        self.concepts = {}
        self.disable = False
        self.errors = [];

    def add(self, key):
        """ Add a token in the question graph to this query object. """
        if key == self.forward_arrow or key == self.back_arrow:
            """ It's a forward arrow, no predicate. """
            self.arrows.append (Edge(direction=key))
        elif isinstance (key, Concept):
            self.order.append (key.name)
            self.concepts[key.name] = key
        elif isinstance (key, Edge):
            self.arrows.append (key)
        elif isinstance(key, list) and len(key) == 3:
            if key[2].endswith(self.forward_arrow):
                self.arrows.append (Edge(direction=self.forward_arrow,
                                         predicate=key[1]))
            elif key[0].startswith(self.back_arrow):
                self.arrows.append (Edge(direction=self.back_arrow,
                                         predicate=key[1]))
        else:
            """ It's a concept identifier, potentially named. """
            type_name = key
            name = key
            if ':' in key:
                if key.count (':') > 1:
                    raise IllegalConceptIdentifierError (f"Illegal concept id: {key}")
                name, type_name = key.split (':')
            self.order.append (name)
            """ Verify the type name is in the model we have. """
            if self.concept_model.get (type_name) == None or type_name not in self.concept_model:
                raise Exception(f'Concept "{type_name}" is not in the concept model.')

            self.concepts[name] = Concept (name=name, type_name=type_name)
    def __getitem__(self, key):
        return self.concepts [key]
    def __setitem__(self, key, value):
        raise ValueError ("Not implemented")
    def __delitem__ (self, key):
        del self.concepts[key]
    def __contains__ (self, key):
        return key in self.concepts
    def __repr__(self):
        return f"{self.concepts} | {self.arrows}"

class QueryPlan:
    """ A plan outlining which schema to use to fulfill a query. """
    def __init__(self):
        self.plan = []
    def add (self, schema_name, schema_url, subj, pred, obj):
        """ Add a mapping between a schema and a query transition. """
        top_schema = None
        if len(self.plan) > 0:
            top = self.plan[-1]
            top_schema = top[0]
            if top_schema == schema_name:
                # this is the next edge in an ongoing segment.
                top[2].append ([ source, predicate, target ])
            else:
                plan.append ([ schema_name, sub_schema_url, [
                    [ source, predicate, target ]
                ]])

class QueryPlanStrategy:
    """ A strategy for developing a query plan given a schema. """

    def __init__(self, backplane):
        """ Construct a query strategy, specifying the schema. """
        self.schema = Schema (backplane)

    def plan (self, query):
        """
        Plan a query over the configured sources and their associated schemas.
        """
        logger.debug (f"--planning query: {query}")
        plan = []
        for index, element_name in enumerate(query.order):
            if index == len(query.order) - 1:
                """ There's another concept to transition to. """
                continue
            self.plan_edge (
                plan=plan,
                source=query.concepts[element_name],
                target=query.concepts[query.order[index+1]],
                predicate=query.arrows[index])
        logger.debug (f"--created plan {plan}")
        return plan

    def plan_edge (self, plan, source, target, predicate):
        """ Determine if a transition between two types is supported by
        any of the registered sub-schemas.
        """
        edge = None
        schema = None
        for schema_name, sub_schema_package in self.schema.schema.items ():
            """ Look for a path satisfying this edge in each schema. """
            sub_schema = sub_schema_package ['schema']
            sub_schema_url = sub_schema_package ['url']
            if source.type_name in sub_schema:
                logger.debug (f"  --{schema_name} - {source.type_name} => {target.type_name}")
                if target.type_name in sub_schema[source.type_name]:
                    """ Matching path. Write it to the plan. """
                    top_schema = None
                    if len(plan) > 0:
                        top = plan[-1]
                        top_schema = top[0]
                    if top_schema == schema_name:
                        # this is the next edge in an ongoing segment.
                        top[2].append ([ source, predicate, target ])
                    else:
                        plan.append ([ schema_name, sub_schema_url, [
                            [ source, predicate, target ]
                        ]])
            else:
                """ No explicit matching plan for this edge. Do implicit conversions make it work? """
                implicit_conversion = BiolinkModelWalker ()
                for conv_type in implicit_conversion.get_transitions (source.type_name):
                    implicit_conversion_schema = "implicit_conversion"
                    implicit_conversion_url = self.schema.schema[implicit_conversion_schema]['url']
                    if conv_type in sub_schema:
                        logger.debug (f"  --impconv: {schema_name} - {conv_type} => {target.type_name}")
                        if target.type_name in sub_schema[conv_type]:
                            plan.append ([
                                implicit_conversion_schema,
                                implicit_conversion_url, [
                                    [ source, predicate, Concept(name=conv_type,
                                                                 type_name=conv_type,
                                                                 include_patterns=target.include_patterns,
                                                                 exclude_patterns=target.exclude_patterns) ]
                                ]])
                            plan.append ([ schema_name, sub_schema_url, [
                                [ Concept(name=conv_type,
                                          type_name=conv_type,
                                          include_patterns=source.include_patterns,
                                          exclude_patterns=source.exclude_patterns), predicate, target ]
                            ]])
