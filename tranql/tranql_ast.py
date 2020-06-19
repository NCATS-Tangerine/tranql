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
from tranql.util import deep_merge, light_merge
from tranql.request_util import async_make_requests
from tranql.util import Text
from tranql.tranql_schema import Schema
from tranql.exception import ServiceInvocationError
from tranql.exception import UndefinedVariableError
from tranql.exception import UnableToGenerateQuestionError
from tranql.exception import MalformedResponseError
from tranql.exception import IllegalConceptIdentifierError
from tranql.exception import UnknownServiceError
from tranql.exception import InvalidTransitionException
from tranql.utils.merge_utils import connect_knowledge_maps

logger = logging.getLogger (__name__)

def truncate (s, max_length=75):
    return (s[:max_length] + '..') if len(s) > max_length else s

class Bionames:
    """ Resolve natural language names to ontology identifiers. """
    url = "https://bionames.renci.org/lookup/{input}/{type}/"

    @staticmethod
    def get_ids (name, type_name):
        url = Bionames.url.format (**{
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
            pass #raise e
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
        self.planner = QueryPlanStrategy (ast.schema)

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
        if isinstance(value, dict):
            if field in value:
                result = value[field]
            else:
                result = None
        return result

    @staticmethod
    def resolve_name (name, type_names):
        if not isinstance(type_names, list):
            type_names = [type_names]
        result = []
        for type_name in type_names:
            equivalent_identifiers = Bionames.get_ids (name, type_name)
            for i in equivalent_identifiers:
                result.append(i["id"])
        for type_name in type_names:
            if type_name == 'chemical_substance':
                response = requests.get (f"http://mychem.info/v1/query?q={name}").json ()
                for obj in response['hits']:
                    if 'chebi' in obj:
                        result.append (obj['chebi']['id'])
                    if 'chembl' in obj:
                        result.append ("CHEMBL:"+obj['chembl']['molecule_chembl_id'])
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
                    if not interpreter.dynamic_id_resolution:
                        raise Exception('Invalid curie "' + value + '". Did you mean to enable dynamic id resolution?')
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
                statement.where = self.where
        self.query.disable = True # = Query ()
        return statements

    def format_constraints(self,interpreter):
        schema = self.get_schema_name(interpreter)
        for enum, constraint in enumerate(self.where):
            """ Add constraints, if they apply to this schema. """
            name, op, val = constraint
            prefix = f"{schema}."
            if name.startswith (prefix):
                """ Remove the schema prefix as we add the constraint. """
                constraint_copy = copy.deepcopy (constraint)
                constraint_copy[0] = name.replace (prefix, "")
                self.where[enum] = constraint_copy

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
                                edge_id = f'{index}_{lastnode["id"]}_{node["id"]}'
                                edges.append (self.edge (
                                    index = edge_id,
                                    source=lastnode['id'],
                                    target=node['id'],
                                    type_name = edge_spec.predicate))
                            else:
                                edge_id = f'{index}_{node["id"]}_{lastnode["id"]}'
                                edges.append (self.edge (
                                    index = edge_id,
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
                        edge_id = f'{index}_{source_id}_{target_id}'
                        question['question_graph']['edges'].append (
                            self.edge (
                                index = edge_id,
                                source = source_id,
                                target = target_id))
                        new_questions.append (self.message (options))
                questions = new_questions
        return questions

    """
    Decorates a result message

    Args:
        response (object) - KGS 0.1.0 Message object.
        options (dict) - Refer to SelectStatement::decorate `options` arg.
    Returns:
        None
    """
    @staticmethod
    def decorate_result(response, options={}):
        if 'knowledge_graph' in response:
            for node in response['knowledge_graph'].get('nodes',[]):
                SelectStatement.decorate(node, True, options)

            for edge in response['knowledge_graph'].get('edges',[]):
                SelectStatement.decorate(edge, False, options)
    """
    Decorates a list of result messages

    Args:
        responses (list<dict>) - List of KGS 0.1.0 Message objects.
        options (dict) - Refer to SelectStatement::decorate `options` arg.
    Returns:
        None
    """
    @staticmethod
    def decorate_results(responses, options={}):
        for response in responses:
            SelectStatement.decorate_result(response, options)
    """
    Decorates a KGraph element

    Args:
        element (dict) - KGS 0.1.0 KNode|KEdge object.
        is_node (bool) - Specifies if the element is a KNode. If False, `element` is treated as a KEdge.
        options (dict) - Information used to decorate the object with. Some may be omitted to avoid decoration.
            {
            schema (str, optional) - The reasoner that the element originates from.
                When omitted, the element will still be given the reasoner attribute, but it will be empty.
            }
    Returns:
        None
    """
    @staticmethod
    def decorate(element, is_node, options):
        if "reasoner" not in element: element["reasoner"] = []
        if "schema" in options:
            if isinstance(options["schema"],str): options["schema"] = [options["schema"]]
            element["reasoner"].extend(options["schema"])
        # Only edges have the source_database property
        if not is_node:
            element["source_database"] = element.get("source_database",["unknown"])

    def get_schema_name(self,interpreter):
        schema = None
        for s in self.planner.schema.config["schema"]:
            # In SelectStatement::execute, it sets self.service to the backplane url so we have to check for that as well
            if (
                self.planner.schema.config["schema"][s]["url"] == self.service or
                self.resolve_backplane_url(self.planner.schema.config["schema"][s]["url"],interpreter) == self.service
            ):
                schema = s
                break
        return schema

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
            """ We want to find what schema name corresponds to the url we are querying.
            Then we can format the constraints accordingly (e.g. the ICEES schema name is 'icces'). """

            self.format_constraints(interpreter)

            self.service = self.resolve_backplane_url (self.service, interpreter)
            questions = self.generate_questions (interpreter)

            [self.ast.schema.validate_question(question) for question in questions]

            root_question_graph = questions[0]['question_graph']

            service = interpreter.context.resolve_arg (self.service)


            """ Invoke the service and store the response. """

            # For each question, make a request to the service with the question
            # Only have a maximum of maximumParallelRequests requests executing at any given time
            logger.setLevel (logging.DEBUG)
            logger.debug (f"Starting queries on service: {service} (asynchronous={interpreter.asynchronous})")
            logger.setLevel (logging.INFO)
            prev = time.time ()
            # We don't want to flood the service so we cap the maximum number of requests we can make to it.
            maximumQueryRequests = 50
            interpreter.context.set('requestErrors',[])
            if interpreter.asynchronous:
                maximumParallelRequests = 4
                responses = async_make_requests ([
                    {
                        "method" : "post",
                        "url" : service,
                        "json" : q,
                        "headers" : {
                            "accept": "application/json"
                        }
                    }
                    for q in questions[:maximumQueryRequests]
                ],maximumParallelRequests)
                errors = responses["errors"]
                responses = responses["responses"]
                interpreter.context.mem.get('requestErrors', []).extend(errors)

            else:
                responses = []
                for index, q in enumerate(questions):
                    logger.debug (f"executing question {json.dumps(q, indent=2)}")
                    response = self.request (service, q)
                    # TODO - add a parameter to limit service invocations.
                    # Until we parallelize requests, cap the max number we attempt for performance reasons.
                    #logger.debug (f"response: {json.dumps(response, indent=2)}")
                    responses.append (response)

                    if index >= maximumQueryRequests:
                        break

            logger.setLevel (logging.DEBUG)
            logger.debug (f"Making requests took {time.time()-prev} s (asynchronous = {interpreter.asynchronous})")
            logger.setLevel (logging.INFO)

            for response in responses:
                response['question_order'] = self.query.order

            if len(responses) == 0:
                # interpreter.context.mem.get('requestErrors',[]).append(ServiceInvocationError(
                #     f"No valid results from {self.service} with query {self.query}"
                # ))
                raise ServiceInvocationError (
                    f"No valid results from service {self.service} executing " +
                    f"query {self.query}. Unable to continue query. Exiting.")
            self.decorate_results(responses, {
                "schema" : self.get_schema_name(interpreter)
            })
            result = self.merge_results (responses, interpreter, root_question_graph, self.query.order)
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
        duplicate_statements = []
        first_concept = None

        # Generate the root statement's question graph
        root_question_graph = self.generate_questions(interpreter)[0]['question_graph']

        for index, statement in enumerate(statements):
            logger.debug (f" -- {statement.query}")
            response = statement.execute (interpreter)
            response['question_order'] = statement.query.order
            responses.append (response)
            duplicate_statements.append (response)
            if index < len(statements) - 1:
                """ Implement handoff. Finds the type name of the first element of the
                next plan segment, looks up values for that type from the answer bindings of the
                last response, and transfers values to the new question. TODO: incorporate
                user specified namnes. """
                next_statement = statements[index+1]
                name = next_statement.query.order [0]
                #name = statement.query.order[-1]
                #values = self.jsonkit.select (f"$.knowledge_map.[*].node_bindings.{name}", response)
                # logger.error (f"querying $.knowledge_map.[*].[*].node_bindings.{name} from {json.dumps(response, indent=2)}")
                first_concept = next_statement.query.concepts[name]
                if statements[index].query.order == next_statement.query.order:
                    first_concept.set_nodes (statements[index].query.concepts[name].nodes)
                else:
                    values = self.jsonkit.select (f"$.knowledge_map.[*].[*].node_bindings.{name}", self.merge_results(duplicate_statements, interpreter, root_question_graph, statements[index].query.order))
                    duplicate_statements = []
                    first_concept.set_nodes (values)
                    if len(values) == 0:
                        print (f"---> {json.dumps(response, indent=2)}")
                        message = f"No valid results from service {statement.service} executing " + \
                                  f"query {statement.query}. Unable to continue query. Exiting."
                        raise ServiceInvocationError (
                            message = message,
                            details = Text.short (obj=f"{json.dumps(response, indent=2)}", limit=1000))
        merged = self.merge_results (responses, interpreter, root_question_graph, self.query.order)
        questions = self.generate_questions (interpreter)
        # merged['question_graph'] = questions[0]['question_graph']
        return merged

    @staticmethod
    def merge_results (responses, interpreter, question_graph, root_order=None):
        """ Merge results. """

        """
        If True, SelectStatement::resolve_name (and therefore the Bionames API) will be called on every node that does not already possess the `equivalent_identifiers` property.
        As of now, this feature should be left disabled as it results in large queries failing due to the flooding of the Bionames API. Additionally, the Bionames class does not use async requests as of now, so it is also quite slow.
        """
        RESOLVE_EQUIVALENT_IDENTIFIERS = interpreter.resolve_names
        """
        If True, all nodes that have identical names will be assumed to be identical nodes and will consequently be merged together.
        """
        NAME_BASED_MERGING = interpreter.name_based_merging

        # result = responses[0] if len(responses) > 0 else None
        result = {
                "knowledge_graph": {
                    "nodes": [],
                    "edges": []
                },
                "knowledge_map": [],
                "question_graph": question_graph
        }
        # if not 'knowledge_graph' in result:
        #     message = "Malformed response does not contain knowledge_graph element."
        #     logger.error (f"{message} svce: {service}: {json.dumps(result, indent=2)}")
        #     raise MalformedResponseError (message)
        kg = result['knowledge_graph']
        #answers = result['answers']
        answers = result['knowledge_map']

        node_map = {}

        replace_edge_ids = []
        if RESOLVE_EQUIVALENT_IDENTIFIERS:
            logger.info ('Starting to fetch equivalent identifiers')
        total_requests = 0
        prev_time = time.time()
        """
        Fetch/create equivalent identifiers for all nodes in the responses.

        Convert the type property on all nodes and edges to a list if it is not already one.
        """
        for response in responses:
            if 'knowledge_graph' in response:
                nodes = response['knowledge_graph'].get('nodes',[])
                edges = response['knowledge_graph'].get('edges',[])
                for node in nodes:
                    """
                    Convert the `type` property of all nodes into a list. Create it if they do not already have it.
                    """
                    if 'type' not in node:
                        node['type'] = []
                    if (not isinstance(node['type'],list)):
                        node['type'] = [node['type']]

                    """
                    Create the `equivalent_identifiers` property on all nodes that do not already have it.
                    """
                    if 'equivalent_identifiers' not in node:
                        ids = [node['id']]
                        if RESOLVE_EQUIVALENT_IDENTIFIERS:
                            ids = SelectStatement.resolve_name (node.get('name',None), node.get('type',''))
                        node['equivalent_identifiers'] = ids
                        total_requests += 1
                    """
                    Give the node its own identifier inside its equivalent identifiers if it doesn't already have it.
                    """
                    if node['id'] not in node['equivalent_identifiers']:
                        node['equivalent_identifiers'].append(node['id'])

                for edge in edges:
                    """
                    Convert the `type` property of all edges into a list. Create it if they do not already have it.
                    """
                    if 'type' not in edge:
                        edge['type'] = []
                    if (not isinstance(edge['type'],list)):
                        edge['type'] = [edge['type']]

        if RESOLVE_EQUIVALENT_IDENTIFIERS:
            logger.info (f'Finished fetching equivalent identifiers for {total_requests} nodes ({time.time()-prev_time}s).')

        """
        For instances where multiple nodes have the same name, infer that they are equivalent and give each equivalent identifiers to one another.
        Note: this infers that if a node has the same `name` property as another, then it be the other. If this ever becomes untrue, it needs to be updated.
        """
        if NAME_BASED_MERGING:
            node_name_map = {}
            for response in responses:
                if 'knowledge_graph' in response:
                    nodes = response['knowledge_graph'].get('nodes',[])
                    for node in nodes:
                        """
                        Add to the node_name_map of duplicate names to nodes
                        """
                        name = node.get('name',None)
                        if name != None:
                            if name not in node_name_map:
                                node_name_map[name] = [node]
                            else:
                                node_name_map[name].append(node)

            for i in node_name_map:
                """
                Assign every node the equivalent_identifiers property of all other nodes with the same name
                """
                nodes = node_name_map[i]
                all_equivalent_identifiers = []
                [all_equivalent_identifiers.extend(node['equivalent_identifiers']) for node in nodes]
                # Filter out all duplicates
                all_equivalent_identifiers = list(set(all_equivalent_identifiers))
                for node in nodes:
                    node['equivalent_identifiers'] = all_equivalent_identifiers


        for response in responses:
            #logger.error (f"   -- Response message: {json.dumps(result, indent=2)}")
            # TODO: Preserve reasoner provenance. This treats nodes as equal if
            # their ids are equal. Consider merging provenance/properties.
            # Edges, we may keep distinct and whole or merge to some tbd extent.
            if 'knowledge_graph' in response:
                rkg = response['knowledge_graph']
                #result['answers'] += response['answers']
                [kg['edges'].append(e) for e in rkg.get('edges',[])]
                # qg = response.get('question_graph',{})
                # result['question_graph']['nodes'].extend(qg.get('nodes',[]))
                # result['question_graph']['edges'].extend(qg.get('edges',[]))
                other_nodes = rkg['nodes'] if 'nodes' in rkg else []
                for n in other_nodes:
                    """
                    If possible, try to convert all nodes to a single identifier so that we don't end up with multiple separate nodes that are actually the same in the graph.
                    Example: https://i.imgur.com/Z76R1wZ.png. The node on left is called "citric acid," and the node on right is called "anhydrous citric acid."
                    The left node's id is "CHEBI:30769" and the right node's id is "CHEMBL:CHEMBL1261." These identifiers are actually equivalent to each other.
                    """
                    ids = n['equivalent_identifiers']
                    exists = False
                    for id in ids:
                        for node_id in node_map:
                            node = node_map[node_id]
                            if id == node_id or id in node['equivalent_identifiers']:
                                exists = True
                                break
                        if exists:
                            replace_edge_ids.append([n["id"], node["id"]])
                            # Ensure that both nodes' properties are represented in the new node.
                            light_merge(node,n)
                            light_merge(n,node)
                            break
                    if not exists:
                        node_map[n['id']] = n
                        kg['nodes'].append (n)
        # We need to update the edges' ids if we changed any node ids.
        for old_id, new_id in replace_edge_ids:
            for edge in result['knowledge_graph'].get('edges',[]):
                if old_id == edge['source_id']:
                    edge['source_id'] = new_id
                if old_id == edge['target_id']:
                    edge['target_id'] = new_id
            # We also need to replace these old identifiers within the knowledge map or bad things will happen.
            for response in responses:
                for answer in response['knowledge_map']:
                    node_bindings = answer.get('node_bindings',{})

                    for concept in node_bindings:
                        identifier = node_bindings[concept]
                        if identifier == old_id:
                            identifier = new_id
                        node_bindings[concept] = identifier


        # Kill all duplicate edges. Merge them into the winning edge.
        # This has to occur after edge ids are replaced so that we can more succesfully detect duplicate edges, since nodes will have been merged into one another.
        merged_edges = []
        killed_edges = []
        for response in responses:
            if 'knowledge_graph' in response:
                rkg = response['knowledge_graph']
                other_edges = rkg['edges'] if 'edges' in rkg else []
                for e in other_edges:
                    exists = False
                    e_type = e.get('type',None)
                    for edge in merged_edges:
                        edge_type = edge.get('type',None)
                        if sorted(edge_type) == sorted(e_type) and edge['source_id'] == e['source_id'] and edge['target_id'] == e['target_id']:
                            exists = True
                            break
                    if exists:
                        light_merge(edge,e)
                        light_merge(e,edge)
                        killed_edges.append ([e['id'], edge['id']])
                    else:
                        merged_edges.append (e)

        # For each killed edge, go through the knowledge_map and replace the dead edge's id with the new edge's id.
        for old_edge_id, new_edge_id in killed_edges:
            for response in responses:
                for answer in response['knowledge_map']:
                    edge_bindings = answer.get('edge_bindings',{})
                    delete = False
                    for concept in edge_bindings:
                        if isinstance(edge_bindings[concept], list):
                            identifiers = []
                            for identifier in edge_bindings[concept]:
                                if identifier == old_edge_id:
                                    identifier = new_edge_id
                                identifiers.append(identifier)
                            edge_bindings[concept] = identifiers
                        else:
                            identifier = edge_bindings[concept]
                            if identifier == old_edge_id:
                                identifier = new_edge_id
                            edge_bindings[concept] = identifier

        kg['edges'] = merged_edges


        result['knowledge_map'] = SelectStatement.connect_knowledge_maps(responses, root_order)


        return result

    @staticmethod
    def connect_knowledge_maps(responses, root_order):
        # Now that all the merging in the knowledge graph is completed, the answers in the knowledge maps must be merged.
        # We need to connect answers from each response together with answers from every other response.
        # For example, given the query `select population_of_individual_organisms->disease->gene`, which is split
        # into two statements: `select population_of_individual_organisms->disease FROM icees` and `select disease->gene FROM robokop`,
        # an answer with `population_of_individual_organisms : "COHORT:X" -> disease : "MONDO:Y"``
        # must be connected to another answer with `disease : "MONDO:Y" -> gene : "HGNC:Z"` in order to form a complete answer.
        # We need the entire path of a query in each answer.
        return connect_knowledge_maps(responses,root_order)
        # result_km = []
        #
        # if len(responses) == 1:
        #     result_km = responses[0]['knowledge_map']
        #
        # elif root_order == None:
        #     for response in responses:
        #         result_km.extend(response['knowledge_map'])
        # else:
        #     ordered_responses = {}
        #     for first_response in responses:
        #         if root_order[0] == first_response['question_order'][0]:
        #             if root_order[0] in ordered_responses:
        #                 ordered_responses[root_order[0]].append (first_response)
        #             else:
        #                 ordered_responses[root_order[0]] = [first_response]
        #
        #     while sum(len(resp) for resp in ordered_responses.values()) < len(responses):
        #         response = list(ordered_responses.values())[-1][0]
        #         next_response_start = response['question_order'][-1]
        #         # print(next_response_start)
        #         for next_response in responses:
        #             if next_response['question_order'][0] == next_response_start:
        #                 if next_response_start in ordered_responses:
        #                     ordered_responses[next_response_start].append (next_response)
        #                 else:
        #                     ordered_responses[next_response_start] = [next_response]
        #
        #     # print (json.dumps(
        #     #     ordered_responses,
        #     #     indent=2
        #     # ))
        #     for enum, current_responses in enumerate(list(ordered_responses.values())):
        #         new_answers = []
        #         if enum + 1 < len(ordered_responses):
        #             next_responses = list(ordered_responses.values())[enum+1]
        #         else:
        #             next_responses = []
        #         # First responses, must be head answers that will be used to build off of.
        #         if enum == 0:
        #             for current_response in current_responses:
        #                 for answer in current_response['knowledge_map']:
        #                     new_answers.append (answer)
        #         root_answers = copy.deepcopy(new_answers)
        #         for current_response in current_responses:
        #             for next_response in next_responses:
        #
        #                 current_response_end = current_response['question_order'][-1]
        #                 next_response_start = next_response['question_order'][0]
        #
        #                 # print([
        #                 #     current_response_end,
        #                 #     next_response_start,
        #                 #     result_km,
        #                 #     next_response['knowledge_map']
        #                 # ])
        #
        #                 for current_answer in root_answers:
        #                     for next_answer in next_response['knowledge_map']:
        #                         current_node_bindings = current_answer['node_bindings']
        #                         current_edge_bindings = current_answer['edge_bindings']
        #
        #                         next_node_bindings = next_answer['node_bindings']
        #                         next_edge_bindings = next_answer['edge_bindings']
        #
        #
        #                         current_last_concept_id = current_node_bindings[current_response_end]
        #                         next_first_concept_id = next_node_bindings[next_response_start]
        #                         # convert if to list if provided as string
        #                         next_first_concept_id = [next_first_concept_id] if isinstance(next_first_concept_id, str) \
        #                                                 else next_first_concept_id
        #                         if current_last_concept_id == next_first_concept_id:
        #                             merged_answer = copy.deepcopy(current_answer)
        #                             merged_answer['node_bindings'].update (next_node_bindings)
        #                             merged_answer['edge_bindings'].update (next_edge_bindings)
        #
        #                             new_answers.append(merged_answer)
        #
        #         result_km = []
        #         dump_map = {}
        #         # Filter duplicates and set new result_km
        #         for answer in new_answers:
        #             dumped = json.dumps(answer)
        #             if dumped not in dump_map:
        #                 dump_map[dumped] = answer
        #                 result_km.append(answer)
        #
        #
        #     # for prev_response in responses:
        #     #     detached = root_order[0] != prev_response['question_order'][0]
        #     #     if not detached:
        #     #         # logger.critical([prev_response['question_order'], 'detached'])
        #     #         result_km.extend(prev_response['knowledge_map'])
        #     #     for response in responses:
        #     #         if prev_response == response: continue
        #     #
        #     #         prev_response_end = prev_response['question_order'][-1]
        #     #         current_response_start = response['question_order'][0]
        #     #
        #     #         # logger.critical([prev_response_end,current_response_start])
        #     #
        #     #         if prev_response_end == current_response_start:
        #     #             prev_knowledge_map = prev_response['knowledge_map']
        #     #             current_knowledge_map = response['knowledge_map']
        #     #             for prev_answer in prev_knowledge_map:
        #     #                 for current_answer in current_knowledge_map:
        #     #                     prev_node_bindings = prev_answer['node_bindings']
        #     #                     prev_edge_bindings = prev_answer['edge_bindings']
        #     #                     current_node_bindings = current_answer['node_bindings']
        #     #                     current_edge_bindings = current_answer['edge_bindings']
        #     #
        #     #                     prev_last_concept_id = prev_node_bindings[prev_response_end]
        #     #                     current_first_concept_id = current_node_bindings[current_response_start]
        #     #
        #     #                     if prev_last_concept_id == current_first_concept_id:
        #     #                         # Merge these two answers and then add the result to the resulting knowledge map
        #     #                         merged_answer = copy.deepcopy(prev_answer)
        #     #                         # Merge node_bindings of current answer into the copied previous answer
        #     #                         merged_answer['node_bindings'].update (current_node_bindings)
        #     #                         # Same for edge_bindings
        #     #                         merged_answer['edge_bindings'].update (current_edge_bindings)
        #     #
        #     #                         result_km.append(merged_answer)
        #
        #
        #         # result_km.append(answer)
        #
        #         # logger.critical([question_graph, response['question_order']])
        #
        # # Filter any answers whose node_bindings aren't the complete path
        # # if root_order != None:
        # #     filtered_result_km = []
        # #     for answer in result_km:
        # #         delete = False
        # #         node_bindings = answer["node_bindings"]
        # #         for qg_node in root_order:
        # #             if qg_node not in node_bindings:
        # #                 delete = True
        # #                 break
        # #         if not delete:
        # #             filtered_result_km.append (answer)
        # #     result_km = filtered_result_km



        # logger.critical(result_km)
        return result_km

class TranQL_AST:
    """Represent the abstract syntax tree representing the logical structure of a parsed program."""

    def __init__(self, parse_tree, schema):
        logger.debug (f"{json.dumps(parse_tree, indent=2)}")
        """ Create an abstract syntax tree from the parser token stream. """
        self.schema = schema
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
        self.errors = []

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

    def __init__(self, schema):
        """ Construct a query strategy, specifying the schema. """
        self.schema = schema

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
        converted = False

        source_type = source.type_name
        target_type = target.type_name
        if predicate.direction == Query.back_arrow:
            source_type, target_type = target_type, source_type

        for schema_name, sub_schema_package in self.schema.schema.items ():
            """ Look for a path satisfying this edge in each schema. """
            sub_schema = sub_schema_package ['schema']
            sub_schema_url = sub_schema_package ['url']

            if source_type in sub_schema:
                logger.debug (f"  --{schema_name} - {source_type} => {target_type}")
                if target_type in sub_schema[source_type]:
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
                    converted = True
            else:
                """ No explicit matching plan for this edge. Do implicit conversions make it work? """
                implicit_conversion = BiolinkModelWalker ()
                for conv_type in implicit_conversion.get_transitions (source_type):
                    implicit_conversion_schema = "implicit_conversion"
                    implicit_conversion_url = self.schema.schema[implicit_conversion_schema]['url']
                    if conv_type in sub_schema:
                        logger.debug (f"  --impconv: {schema_name} - {conv_type} => {target_type}")
                        if target_type in sub_schema[conv_type]:
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
                            converted = True
        if not converted:
            source_target_predicates = self.explain_predicates (source_type, target_type)
            target_source_predicates = self.explain_predicates (target_type, source_type)
            raise InvalidTransitionException (
                source,
                target,
                predicate,
                explanation=''.join ([
                    "Valid transitions in the federated schema between the given types are: \n",
                    f"{source_type}->{target_type}: {json.dumps(source_target_predicates, indent=2)}\n",
                    f"{target_type}->{source_type}: {json.dumps(target_source_predicates, indent=2)} "
                ]))

    def explain_predicates (self, source_type, target_type):
        list_of_lists = [
            sub_schema_package['schema'].get (source_type,{}).get (target_type, [])
            for schema_name, sub_schema_package in self.schema.schema.items ()
        ]
        return [ i for li in list_of_lists for i in li ]
