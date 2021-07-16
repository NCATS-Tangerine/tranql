import copy
import json
import logging
import requests
import requests_cache
import traceback
import time # Basic time profiling for async
import yaml
import importlib.machinery
import os.path
from tranql.concept import ConceptModel
from tranql.concept import BiolinkModelWalker
from tranql.util import Concept
from tranql.util import JSONKit
from tranql.util import light_merge
from tranql.request_util import async_make_requests
from tranql.util import Text, snake_case
from tranql.exception import ServiceInvocationError
from tranql.exception import UndefinedVariableError
from tranql.exception import IllegalConceptIdentifierError
from tranql.exception import UnknownServiceError
from tranql.utils.merge_utils import merge_messages
from PLATER.services.util.graph_adapter import GraphInterface

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

class CustomFunctions:
    def __init__(self):
        self.functions = self.load_functions()

    @staticmethod
    def load_functions():
        functions = {}
        with open(os.path.join(os.path.dirname(__file__), "udfs.yaml"), "r") as f:
            udf_data = yaml.safe_load(f.read())
            modules = udf_data["userDefinedFunctions"]["modules"]
            for udf_module in modules:
                source_file = udf_module["source"]
                udf_functions = udf_module["functions"]

                file_path = os.path.join(os.path.dirname(__file__), source_file)

                loader = importlib.machinery.SourceFileLoader(file_path, file_path)
                module = loader.load_module()

                for function_name in udf_functions:
                    functions[function_name] = getattr(module, function_name)

        return functions

    """ Intended for use as a decorator """
    def custom_function(self, function, name=None):
        if name is None: name = function.__name__
        self.functions[name] = function

    def resolve_function(self, parsed_function):
        function_name = parsed_function["name"]
        # For every arg passed in, recurse if it is a function to resolve its value
        function_args = []
        keyword_arguments = {}
        # Will recurse to resolve the value of a function argument
        make_not_function = lambda argument_value: self.resolve_function(argument_value) if isinstance(argument_value, dict) else argument_value
        # Go through and make sure every argument isn't a nested function
        # Also handle keyword arguments
        for argument in parsed_function["args"]:
            # kwarg
            if isinstance(argument, list):
                arg_name = argument[0]
                arg_value = argument[2]
                keyword_arguments[arg_name] = make_not_function(arg_value)
            # normal arg
            else:
                function_args.append(make_not_function(argument))

        return self.functions[function_name](*function_args, **keyword_arguments)


custom_functions = CustomFunctions()

""" How to define a function directly using decorator. Can also refer to unit tests for more examples """
@custom_functions.custom_function
def mirror(x):
    return x


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

    def message (self, q_nodes: dict=None,
                 q_edges: dict=None,
                 k_nodes: dict=None,
                 k_edges: dict=None,
                 options: dict=None):
        """ Generate the frame of a question. """
        return {
            "message": {
                "query_graph": {
                    "edges": q_edges or {} ,
                    "nodes": q_nodes or {}
                },
                "knowledge_graph" : {
                    "nodes" : k_nodes or {},
                    "edges" : k_edges or {}
                },
                "results": []
            },
            "options": options
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

    def edge(self, source, target, type_name=None):
        """ Generate a question edge. """
        e = {
            "subject": source,
            "object": target
        }
        if type_name is not None:
            e["predicate"] = type_name
        return e



    def node(self, type_name, curies=None, **kwargs):
        """ Generate a question node. """
        n = {
            "category": type_name
        }
        if len(curies):
            n['id'] = curies
        # Add other attributes to the node.
        # Used as filters possibly in KP.
        n.update(kwargs)
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
        type_names = [snake_case(type_name.replace('biolink:', '')) for type_name in type_names]
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

    def expand_nodes(self, interpreter, concept: Concept):
        """ Expand variable expressions to nodes. """
        new_nodes = []
        for value in concept.curies:
            if value.startswith ("$"):
                varname = value
                value = interpreter.context.resolve_arg (varname)
                logger.debug (f"resolved {varname} to {value}")
                if value == None:
                    raise UndefinedVariableError (f"Undefined variable: {varname}")
                elif isinstance (value, str):
                    new_nodes.append(value)
                elif isinstance(value, list):
                    """ Binding multiple values to a node. """
                    new_nodes += value
                else:
                    raise TranQLException (
                        f"Internal failure: object of unhandled type {type(value)}.")
                # if variable was something like $x = ['CHEBI:123', 'water'] we need to Curiefy 'water'
                concept.set_curies(new_nodes)
                new_nodes = self.expand_nodes(interpreter, concept)
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
                    new_nodes.append(self.resolve_name (value, concept.type_name))
                    logger.debug (f"resolved {value} to identifiers: {new_nodes}")
                else:
                    """ This is a single curie. Bind it to the node. """
                    new_nodes.append(value)
        concept.set_curies(new_nodes)
        return new_nodes

    def is_bound(self):
        """ Returns true if curie has been set to any of the statements concepts."""
        concepts = self.query.concepts
        for c in concepts:
            nodes = concepts[c].nodes
            bound = any(map(lambda node: bool(node.get('curie', False)), nodes))
            if bound:
                return bound
        return False

    def sort_plan(self, plan):
        # sort the plan such that statements with bound curies are executed first
        sorted_plan = []
        is_bound = False
        start = None
        # find a bound plan
        for p in plan:
            start = p[2]
            # is bound if the start  or the end of the plan is bound
            is_bound = len(start[0][0].curies) or len(start[-1][2].curies)
            if is_bound:
                break
        if is_bound:
            # find plans bound to the same concept that add them as starting queries
            for other_plan in plan:
                bound_concept = start[0][0] if len(start[0][0].curies) else start[-1][2]
                if bound_concept.name == other_plan[2][0][0].name or bound_concept.name == other_plan[2][-1][2].name:
                    sorted_plan.append(other_plan)
            # add other bound / unbound plans in a sequence that preserves
            # connectivity
            while len(sorted_plan) != len(plan):
                for p in [x for x in plan if x not in sorted_plan]:
                    is_connected = False
                    for processed_plan in sorted_plan:
                        # find any statement already added that ensures connectivity
                        all_node_names = []
                        for x in processed_plan[2]:
                            for item in x:
                                if isinstance(item, Concept):
                                    all_node_names.append(item.name)
                        is_connected = p[2][-1][2].name in all_node_names or \
                                       p[2][0][0].name in all_node_names
                        if is_connected:
                            break
                    if is_connected:
                        connected_plan = p
                        # add other plans that match this pattern as next
                        for other_plans in plan:
                            if other_plans[2] == connected_plan[2]:
                                sorted_plan.append(other_plans)
                        # break for loop since we changed list and while loop will resume
                        break
        else:
            # we don't have any bound nodes so continue executing as previous
            sorted_plan = plan
        return sorted_plan

    def plan (self, plan):
        """ Plan a query that may span reasoners. This uses a configured schema to determine
        what kinds of queries each reasoner can respond to. """
        statements = []
        sorted_plan = self.sort_plan(plan)
        for phase in sorted_plan:
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

    def get_TRAPI_options(self, interpreter):
        options = {}
        for constraint in self.where:
            """ This is where we pass constraints to a service. We do this only for constraints
            which do not refer to elements in the query. """
            logger.debug(f"manage constraint: {constraint}")
            name, op, value = constraint
            value = interpreter.context.resolve_arg(value)
            if not name in self.query:
                """
                This is not constraining a concept name in the graph query.
                So interpret it as an option to the underlying service.
                """
                options[name] = constraint[1:]
        return options

    def generate_questions(self, interpreter):
        """
        Given an archetype question graph and values, generate question
        instances for each value permutation.
        """
        questions = []
        # Get options from where clause.
        options = self.get_TRAPI_options(interpreter=interpreter)
        nodes = {}
        edges = {}
        for index, concept_query_id in enumerate(self.query.order):
            """ Expand and filter nodes. """
            concept = self.query[concept_query_id]
            if len(concept.curies) > 0:
                self.expand_nodes (interpreter, concept)
                logger.debug(f"concept--nodes: {concept.curies}")
                filters = interpreter.context.resolve_arg ('$id_filters')
                if filters:
                    filters = [f.lower() for f in filters.split(",")]
                    concept.set_curies([
                        n for n in concept.curies
                        if not n.split(':')[0].lower() in filters
                    ])
            # add node
            node = self.node(
                concept.type_name,
                concept.curies
            )
            nodes[concept.name] = node
            if index == 0:
                # skip first index for edge computing.
                continue
            # add edges
            last_node_name = self.query.order[index -1]
            edge_spec = self.query.arrows[index - 1]
            if edge_spec.direction == self.query.forward_arrow:
                subject = last_node_name
                object = concept_query_id
            else:
                subject = concept_query_id
                object = last_node_name
            edge_id = f'e{index}_{subject}_{object}'
            predicate = edge_spec.predicate
            query_graph_edge = self.edge(
                source=subject,
                target=object,
                type_name=predicate
            )
            edges[edge_id] = query_graph_edge
        question_graph = self.message(
            q_nodes = nodes,
            q_edges = edges,
            options= options
        )
        return question_graph

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
            nodes = response['knowledge_graph'].get('nodes', {})
            edges = response['knowledge_graph'].get('edges', {})
            for node_id in nodes:
                nodes[node_id]['id'] = node_id
                SelectStatement.decorate(nodes[node_id], True, options)
            for edge_id in edges:
                edges[edge_id]['id'] = edge_id
                SelectStatement.decorate(edges[edge_id], False, options)
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
        attributes = element.get('attributes', {})
        has_reasoner_attribute = False
        schema = []
        if "schema" in options:
            # Convert schema to list
            if isinstance(options["schema"], str): options["schema"] = [options["schema"]]
            schema = options["schema"]

        for attribute in attributes:
            if attribute.get('name') == 'reasoner':
                has_reasoner_attribute = True
                attribute['value'] = attribute.get('value', [])
                attribute['value'] = attribute['value'] if isinstance(attribute['value'], list) else [attribute['value']]
                attribute['value'] += schema
                attribute['value'] = list(set(attribute['value']))
                attribute['type'] = 'EDAM:data_0006'
        if not has_reasoner_attribute:
            element['attributes'] = element.get('attributes', [])
            element['attributes'].append({
                'name': 'reasoner',
                'value': schema,
                'type': 'EDAM:data_0006'
            })
        # Add Source database
        # @TODO properly add edge source if not provided

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
        all_schemas = interpreter.schema.config['schema']
        redis_key = [
            key for key in all_schemas
            if 'redis' in all_schemas[key] and self.service.startswith(key + ':')
        ]
        if len(redis_key):
            redis_key = redis_key[0]
            redis_connection_details = all_schemas[redis_key]['redis_connection_params']
            service_name, graph_name = self.service.split(':')
            redis_connection_details.update(
                {
                    'auth': ('', interpreter.config.get(service_name.upper() +'_PASSWORD','')),
                    'db_name': graph_name,
                    'db_type': 'redis',
                }
            )
            graph_interface = GraphInterface(
                **redis_connection_details
            )
            question = self.generate_questions(interpreter)
            import asyncio
            options = question.get('options')
            limit = options.get('limit', [])
            skip = options.get('skip', [])
            cypher_query_options = {}
            if limit:
                cypher_query_options['limit'] = limit[-1]
            if skip:
                cypher_query_options['skip'] = skip[-1]
            answer = asyncio.run(graph_interface.answer_trapi_question(question['message']['query_graph'], options=cypher_query_options))
            response = {'message': answer}
            # Adds source db as reasoner attr in nodes and edges.
            self.decorate_result(response['message'], {
                "schema": self.service
            })
        elif self.service == "/schema":
            response = self.execute_plan (interpreter)
        else:
            """ We want to find what schema name corresponds to the url we are querying.
            Then we can format the constraints accordingly (e.g. the ICEES schema name is 'icces'). """

            self.format_constraints(interpreter)

            self.service = self.resolve_backplane_url (self.service, interpreter)
            question = self.generate_questions (interpreter)

            self.ast.schema.validate_question(question['message'])

            root_question_graph = question["message"]['query_graph']

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
                response = async_make_requests ([
                    {
                        "method" : "post",
                        "url" : service,
                        "json" : question,
                        "headers" : {
                            "accept": "application/json"
                        }
                    }
                ],maximumParallelRequests)
                errors = response["errors"]
                response = response["responses"][0] if len(response["responses"]) else {}
                interpreter.context.mem.get('requestErrors', []).extend(errors)
            else:
                response = {}
                # for index, q in enumerate(questions):
                logger.debug (f"executing question {json.dumps(question, indent=2)}")
                response = self.request (service, question)
                # TODO - add a parameter to limit service invocations.
                # Until we parallelize requests, cap the max number we attempt for performance reasons.
                #logger.debug (f"response: {json.dumps(response, indent=2)}")
                # responses.append (response)

            logger.info (f"Making request to {service} took {time.time()-prev} s (asynchronous = {interpreter.asynchronous})")
            total_results = len(response.get('message',{}).get('results',[]))
            logger.info(f"Got {total_results} results from {service}. for {self.query.order} ")

            response['question_order'] = self.query.order

            if len(response) == 0:
                # @TODO might not be a proper error checking.
                interpreter.context.mem.get('requestErrors',[]).append(ServiceInvocationError(
                    f"No valid results from {self.service} with query {self.query}"
                ))
            else:
                self.decorate_result(response['message'], {
                    "schema" : self.get_schema_name(interpreter)
                })
            # result = self.merge_results (responses, interpreter, root_question_graph, self.query.order)
        interpreter.context.set('result', response)
        """ Execute set statements associated with this statement. """
        for set_statement in self.set_statements:
            logger.debug (f"{set_statement}")
            set_statement.execute (interpreter, context = { "result" : response })
        return response

    def execute_plan (self, interpreter):
        """ Execute a query using a schema based query planning strategy. """
        self.service = ''
        plan = self.planner.plan (self.query)
        statements = self.plan (plan)
        responses = []
        duplicate_statements = []
        first_concept = None

        # Generate the root statement's question graph
        root_question_graph = self.generate_questions(interpreter)['message']['query_graph']

        for index, statement in enumerate(statements):
            logger.debug (f" -- {statement.query}")
            response = statement.execute (interpreter)
            response['question_order'] = statement.query.order
            response['service'] = statement.get_schema_name(interpreter)
            responses.append (response)
            duplicate_statements.append (response)
            if index < len(statements) - 1:
                """ Implement handoff. Finds the type name of the first element of the
                next plan segment, looks up values for that type from the answer bindings of the
                last response, and transfers values to the new question. TODO: incorporate
                user specified names. """
                next_statement = statements[index+1]
                if statements[index].query.order == next_statement.query.order:
                    name = next_statement.query.order[0]
                    first_concept = next_statement.query.concepts[name]
                    first_concept.set_curies (statements[index].query.concepts[name].curies)
                else:
                    name = [name for name in statements[index].query.order if name in next_statement.query.order][0]
                    first_concept = next_statement.query.concepts[name]
                    values = self.jsonkit.select(f"$.knowledge_map.[*].[*].node_bindings.{name}",
                                                  self.merge_results(duplicate_statements,
                                                                     interpreter,
                                                                     root_question_graph,
                                                                     statements[index].query.order)
                                                  )
                    tried_kps = list(map(lambda x: x['service'], duplicate_statements))
                    if len(values) == 0:
                        message = f"No valid results from service { ','.join(tried_kps) } executing " + \
                                  f"query {statement.query}. Unable to continue query. Exiting."
                        raise ServiceInvocationError (
                            message = message,
                            details = Text.short (obj=f"{json.dumps(response, indent=2)}", limit=1000))
                    duplicate_statements = []
                    first_concept.set_curies(values)
        merged = self.merge_results (responses)
        return merged

    @staticmethod
    def merge_results (responses):
        return {"message": merge_messages([response["message"] for response in responses])}


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
                            var, op, val = condition
                            if isinstance(val, dict):
                                val = custom_functions.resolve_function(val)
                            select.where.append ([var, op, val])

                            if var in select.query:
                                if op == '=':
                                    select.query[var].set_curies ([val])
                                elif op == '=~':
                                    select.query[var].include_patterns.append (val)
                                elif op == '!=~':
                                    select.query[var].exclude_patterns.append (val)
                                # the '=' operator already fulfills the purpose of the 'in' operator because you can pass a list into it
                                # elif op == 'in':
                                #     if not isinstance(val, list):
                                #         raise ValueError(f'"in" operator received invalid type {type(val)}')
                                #     select.query[var].set_nodes ( val )

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
            predicate = f'biolink:{key[1]}'
            if key[2].endswith(self.forward_arrow):
                self.arrows.append (Edge(direction=self.forward_arrow,
                                         predicate=predicate))
            elif key[0].startswith(self.back_arrow):
                self.arrows.append (Edge(direction=self.back_arrow,
                                         predicate=predicate))
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
            # @TODO there is a canned version of this for possible swapping
            # Add bmt here(?) needs access to bmt git repo (i.e internet connection)

            if self.concept_model.get (type_name) == None or type_name not in self.concept_model:
                raise Exception(f'Concept "{type_name}" is not in the concept model.')
            # For now just do manual string manipulation for type name
            type_name = f'biolink:' + type_name.replace('_', ' ').title().replace(' ', '')
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

        source_type = snake_case(source.type_name.replace('biolink:', ''))
        target_type = snake_case(target.type_name.replace('biolink:', ''))
        if predicate.direction == Query.back_arrow:
            source_type, target_type = target_type, source_type

        for schema_name, sub_schema_package in self.schema.schema.items ():
            """ Look for a path satisfying this edge in each schema. """
            # This will restrict usage of TRANQL with redis graph
            # Explicitly i.e its either /schema or a redis backend
            # @TODO handle this more elegantly
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

    def explain_predicates (self, source_type, target_type):
        list_of_lists = [
            sub_schema_package['schema'].get (source_type,{}).get (target_type, [])
            for schema_name, sub_schema_package in self.schema.schema.items ()
        ]
        return [ i for li in list_of_lists for i in li ]
