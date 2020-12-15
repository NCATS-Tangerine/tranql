from flask import Flask, request, Response, jsonify
from flask_restful import Api, Resource, abort

class StandardAPIResource(Resource):

    def __init__(self):
        super().__init__()

    @staticmethod
    def validate(request, definition, no_abort=False):
        if not isinstance(request, dict):
            request = request.json
        valid = True
        try:
            pass
            # For some reason this method doesn't work...
            # Validate(request, definition, specs=template)
        except Exception as e:
            valid = False

        if no_abort:
            return valid

        if not valid:
            abort(
                500,
                message="Invalid "+definition,
                status="error",
                code="invalid_arguments"
            )

    def get_opt(self, request, opt):
        return request.get('option', {}).get(opt)

    def rename_key(self, obj, old, new, default=None):
        if old in obj:
            obj[new] = obj.pop (old)

    def rename_key_list(self, node_list, old, new):
        for n in node_list:
            self.rename_key (n, old, new)

    def format_as_query(self, message):
        question_graph = message['question_graph']

        for node in question_graph.get('nodes',[]):
            node['node_id'] = node['id']
            del node['id']
        for edge in question_graph.get('edges',[]):
            edge['edge_id'] = edge['id']
            del edge['id']

        return {
            "query_message": {
                "query_graph": question_graph
            }
        }

    def merge_results(self, message):
        results = message['results']
        del message['results']
        if 'knowledge_graph' not in message:
            message['knowledge_graph'] = {
                "edges": [],
                "nodes": []
            }
        if 'knowledge_map' not in message:
            message['knowledge_map'] = []
        nodeIds = []
        for result in results:
            # Convert 0.9.0 equivalent of knowledge_map to the knowledge_map format we want
            node_bindings = result.get('node_bindings',{})
            edge_bindings = result.get('edge_bindings',{})

            if node_bindings != None and edge_bindings != None:
                message['knowledge_map'].append({
                    "node_bindings": node_bindings,
                    "edge_bindings": edge_bindings
                })


            result = result.get('result_graph', {})

            nodes = result.get('nodes',[])
            edges = result.get('edges',[])

            message['knowledge_graph']['edges'].extend(edges)
            for node in nodes:
                if not node['id'] in nodeIds:
                    message['knowledge_graph']['nodes'].append(node)
                    nodeIds.append(node['id'])
        return message

    def down_cast_message(self, message, reasoner_spec_version='2.0', down_cast_to='0.9'):
        if reasoner_spec_version == '2.0':
            assert 'query_graph' in message
            assert 'knowledge_graph' in message
            assert 'results' in message
            if down_cast_to == '0.9':
                converted_results = []
                for r in message['results']:
                    node_bindings = r['node_bindings']
                    edge_bindings = r['edge_bindings']
                    # Expecting
                    # {qg_id: 'qg-id-value', kg_id: 'kg-id-value'}
                    # tranform to {'qg-id-value': 'kg-id-value'}
                    node_bindings = {n['qg_id']: n['kg_id']for n in node_bindings}
                    edge_bindings = {e['qg_id']: e['kg_id']for e in edge_bindings}
                    r['node_bindings'] = node_bindings
                    r['edge_bindings'] = edge_bindings
                    converted_results.append(r)
                message['results'] = converted_results
                return self.normalize_message(message)

    def normalize_message(self, message):
        if 'results' in message:
            return self.normalize_message(self.merge_results(message))
        if 'answers' in message:
            message['knowledge_map'] = message.pop ('answers')
        ''' downcast 0.9.1 to 0.9 '''
        ''' alter once tranql AST speaks 0.9.1 '''
        self.rename_key (message, old='query_graph', new='question_graph')
        self.rename_key (message, old='machine_question', new='question_graph')
        self.rename_key (message, old='query_options', new='options')
        if not 'knowledge_graph' in message:
            message['knowledge_graph'] = message.get('return value',{}).get('knowledge_graph', {})
        ''' SPEC: for icees, it's machine_question going in and question_graph coming out (but in a return value)? '''
        ''' return value is only an issue for ICEES '''
        if not 'knowledge_map' in message:
            message['knowledge_map'] = message.get('return value',{}).get('answers', [])
        if not 'question_graph' in message:
            message['question_graph'] = message.get('return value',{}).get('question_graph', {})
        self.rename_key_list (message.get('question_graph',{}).get('nodes',[]),
                              old='node_id',
                              new='id')
        self.rename_key_list (message.get('question_graph',{}).get('edges',[]),
                              old='edge_id',
                              new='id')
        return message

    @staticmethod
    def response(data):
        status_code = 200

        is_error = isinstance(data, dict) and 'status' in data and 'code' in data and 'message' in data

        if is_error:
            status_code = 500
        return (data, status_code)

