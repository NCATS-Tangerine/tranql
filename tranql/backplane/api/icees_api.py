import requests
import json
from flask import request, Response
from tranql.backplane.api.standard_api import StandardAPIResource
from tranql.config import config
import string
import logging

logger = logging.getLogger(__name__)

#######################################################
##
## ICEES - Wrapping ICEES Clinical Reasoner Operations
##
#######################################################
class ICEESClusterArgs:
    def __init__(
            self,
            cohort_id="COHORT:22",
            feature_id="EstResidentialDensity",
            value="1",
            operator=">",
            max_p_val="0.5"):
        self.cohort_id = cohort_id
        self.feature_id = feature_id
        self.value = value
        self.operator = operator
        self.max_p_val = max_p_val


class ICEESSchema(StandardAPIResource):
    def __init__(self):
        self.version_to_url_map = {
            "icees": config.get("ICEES_URL").rstrip('/') + "/knowledge_graph/schema",
            "icees3_and_epr": config.get("ICEES3_AND_EPR_URL").rstrip('/') + "/knowledge_graph/schema"
        }

    def get(self):
        """
        ICEES schema
        ---
        tags: [schema]
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
        parameters:
        - description: Either icees or icees3_and_epr
          in: query
          schema:
            type: string
            example: icees
          name: "provider"
        responses:
            '200':
                description: Schema
                content:
                    application/json:
                        schema:
                            type: object
                            example:
                                population_of_individual_organisms:
                                    phenotypic_feature:
                                        - association
                                    named_thing:
                                        - association
                                    activity_and_behavior:
                                        - association
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'
        """
        icees_version = request.args.get('provider')
        if not icees_version:
            self.response({
                "status": "error",
                "code" : "400",
                "message": "Bad request. Need to provide version as get parameter."
            })

        self.schema_url = self.version_to_url_map.get(icees_version)
        if not self.schema_url:
            self.response({
                "status": "error",
                "code": "500",
                "message": f"The specified ICEES version could not be found - {icees_version}"
            })
        response = requests.get(
            self.schema_url,
            verify=False)
        if not response.ok:
            return self.response({
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad ICEES schema response. url: {self.schema_url} request: {request.json} response: {response.text}."
            })
        elif 'return value' in response.json():
            return self.response(response.json()['return value'])
        else:
            return self.response({
                'status': 'error',
                'message': 'Unrecognized response from ICEES schema',
                'code': 'service_invocation_failure'
            })


class ICEESClusterQuery(StandardAPIResource):
    """ ICEES Resource. """
    def __init__(self):
        self.version_to_url_map = {
            "icees": config.get("ICEES3_AND_EPR_URL").rstrip('/') + "/knowledge_graph",
            "icees3_and_epr": config.get("ICEES3_AND_EPR_URL").rstrip('/') + "/knowledge_graph"
        }
        self.synonymization_supported_types = []

    def post(self):
        """
        ICEES query
        ---
        tags: [query]
        description: Query the ICEES clinical reasoner for associations between population clusters and chemicals.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
                    example:
                        knowledge_graph:
                            nodes: []
                            edges: []
                        knowledge_maps:
                            - {}
                        question_graph:
                            nodes:
                                - id: "cohort_diagnosis"
                                  type: "disease"
                                  curie: "MONDO:0004979"
                                - id: "diagnoses"
                                  type: "disease"
                            edges:
                                - id: "e1"
                                  source_id: "cohort_diagnosis"
                                  target_id: "diagnoses"
                        options:
                            Sex:
                                - "="
                                - "0"
                            cohort:
                                - "="
                                - "all_patients"
                            max_p_value:
                                - "="
                                - "1"
        responses:
            '200':
                description: Message
                content:
                    application/json:
                        schema:
                            ref: '#/definitions/Message'
            '500':
                description: An error was encountered
                content:
                    application/json:
                        schema:
                            $ref: '#/definitions/Error'

        """
        self.validate(request, 'Message')
        icees_version = request.args.get('provider', 'icees')
        request.json['options'] = self.compile_options (request.json['options'])

        ''' Give ICEES the spec version it wants.
        We have multiple versions of the spec live at once.
        Until these stabilize and converge, we adapt between them in various ways.
        '''

        for e in request.json['question_graph']['edges']:
            e['type'] = 'association'
        request.json['query_options'] = request.json.pop('options')
        request.json['machine_question'] = request.json.pop('question_graph')
        for bad in [ 'knowledge_graph', 'knowledge_maps' ]:
            if bad in request.json:
                 del request.json[bad]

        result = {}
        ''' Invoke ICEES '''
        icees_kg_url = self.version_to_url_map.get(icees_version) #"https://icees.renci.org/2.0.0/knowledge_graph"
        if not icees_version:
            self.response({
                "status": "error",
                "code": "500",
                "message": f"The specified ICEES version could not be found - {icees_version}"
            })
        logger.debug(f"--request.json({icees_kg_url})--> {json.dumps(request.json, indent=2)}")
        response = requests.post (icees_kg_url,
                                  json=request.json,
                                  verify=False)
        response_json = response.json()
        its_an_error = response_json.\
                       get('return value',{}).\
                       get ('message_code',None) == 'Error'
        if response.status_code >= 300 or its_an_error:
            result = {
                "status": "error",
                "code": "service_invocation_failure",
                "message": f"Bad ICEES response. url: {icees_kg_url} request: {request.json} response: {response.text}.",
                "query": request.json,
                "response": response_json
            }
            logger.info(f"ICEES-ERROR: {json.dumps(result,indent=2)}")
        else:
            logger.info(f"ICEES-NOMINAL: {json.dumps(result,indent=2)}")
            result = self.normalize_message(response_json)
        result = self.synonymize(result)
        return self.response(result)

    def get_supported_type(self):
        # list of entities that are too high level
        exclusion_list = ['named_thing', 'organismal_entity', 'organism_taxon', 'biological_entity', 'genomic_entity']
        exclusion_list = [self.curify_type(x) for x in exclusion_list]
        if not self.synonymization_supported_types:
            base_url = 'https://nodenormalization-sri.renci.org'
            supported_semantic_types = list(filter(lambda x: x not in exclusion_list, requests.get(
                f'{base_url}/get_semantic_types'
            ).json()['semantic_types']['types']))
            supported_descendants = []
            for tp in supported_semantic_types:
                response = requests.get(f'https://bl-lookup-sri.renci.org/bl/{tp}/descendants?version=latest')
                if response.status_code == 200:
                    supported_descendants += response.json()
            self.synonymization_supported_types = set(supported_semantic_types + supported_descendants)
        return self.synonymization_supported_types

    def curify_type(self, concept_type_str):
        """
        Converts to biolink:TypeOfConcept from type_of_concept
        :param concept_type_str
        :return: pascal case of type with prefix biolink:
        """
        if concept_type_str.startswith('biolink:'):
            return concept_type_str
        return 'biolink:' + string.capwords(concept_type_str.replace('_', ' '), ' ').replace(' ', '')

    def synonymize(self, response):
        knowledge_map_key = 'knowledge_map'
        knowledge_graph_key = 'knowledge_graph'
        query_graph_key = 'question_graph'
        knowledge_graph = response[knowledge_graph_key]
        knowledge_map = response[knowledge_map_key]
        query_graph = response[query_graph_key]
        base_url = 'https://nodenormalization-sri.renci.org'
        supported_semantic_types = self.get_supported_type()
        supported_q_ids = [x['id'] for x in query_graph['nodes'] if self.curify_type(x['type']) in supported_semantic_types]
        node_ids = set([x['id'] for x in knowledge_graph['nodes'] if self.curify_type(x['type']) in supported_semantic_types])
        chunk_size = 2000
        curie_params = [f'curie={x}' for x in node_ids]
        chunked_curie_params = [curie_params[start: start + chunk_size] for start in
                                range(0, len(curie_params), chunk_size)]
        response = {}
        for chunk in chunked_curie_params:
            r = {}
            try:
                full_url = f'{base_url}/get_normalized_nodes?{"&".join(chunk)}'
                r = requests.get(full_url).json()
                response.update(r)
            except:
                print(f'error making request {full_url}')

        # replace supported types only careful not to replace other types like population_of_individual_organisms
        # also keep track of things in supported type but failed to be synonymized (going to remove traces of these)
        keep_nodes = [node['id'] for node in knowledge_graph['nodes'] if self.curify_type(node['type']) not in supported_semantic_types or
                      response.get(node['id'])]

        filtered_nodes = list(filter(lambda node: node['id'] in keep_nodes, knowledge_graph['nodes']))
        filtered_edges = list(filter(lambda edge: edge['source_id'] in keep_nodes and edge['target_id'] in keep_nodes,
                                     knowledge_graph['edges']))
        filtered_knowledge_map = list(filter(lambda answer: all([(answer['node_bindings'][key] in keep_nodes)
                                                                 for key in answer['node_bindings']
                                                                 if key in supported_q_ids]), knowledge_map))
        # now we will assign names and main ids for all the ones we know mapped
        for node in filtered_nodes:
            # make sure we are not bumping into unsupported node types
            if node['id'] in keep_nodes and self.curify_type(node['type']) in supported_semantic_types:
                node_data = response[node['id']]
                norm_id = node_data['id']['identifier']
                # default back to node name
                norm_label = node_data['id'].get('label', '')
                equivalent_ids = [eq['identifier'] for eq in node_data['equivalent_identifiers']]
                if not norm_label:
                    other_labels = [eq['label'] for eq in node_data['equivalent_identifiers'] if eq.get('label')]
                    # pick first one else default back to the node's original
                    norm_label = other_labels[0] if len(other_labels) else node['name']
                node['id'] = norm_id
                node['equivalent_identifiers'] = equivalent_ids
                node['name'] = norm_label

        for edge in filtered_edges:
            if edge['source_id'] in response and response[edge['source_id']]:
                edge['source_id'] = response[edge['source_id']]['id']['identifier']
            if edge['target_id'] in response and response[edge['target_id']]:
                edge['target_id'] = response[edge['target_id']]['id']['identifier']

        for bindings in filtered_knowledge_map:
            node_bindings = bindings['node_bindings']
            for q_id in supported_q_ids:
                if q_id in node_bindings:
                    if node_bindings[q_id] in keep_nodes:
                        node_bindings[q_id] = response[node_bindings[q_id]]['id']['identifier']

        return {
            query_graph_key: query_graph,
            knowledge_graph_key: {
                'nodes': filtered_nodes,
                'edges': filtered_edges
            },
            knowledge_map_key: filtered_knowledge_map
        }

    def compile_options (self, options):
        """ Compile input options into icees appropriate format. """
        result = {}
        for k in options.keys ():
            val = options[k]
            if '.' in k:
                ''' Make a nested structure. Turn `icees.feature.X = y` into a nested dict. '''
                levels = k.split ('.')
                obj = result
                for index, level in enumerate(levels):
                    if index < len(levels) - 1:
                        last = obj
                        obj = obj.get(level, {}) if level != 'feature' else {} # we only allow one feature, last feature
                                                                               # is the winner
                        last[level] = obj
                    else:
                        obj[level] = {
                            'operator': val[0],
                            'value': val[1]
                        }
            else:
                ''' assign directly. '''
                result[k] = val[1]

        """ Filter ids returned by ICEES to ones we can currently make use of. """
        return result
