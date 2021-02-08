import json
import os

class MockHelper:
    def get_obj (self, file_name):
        """ Get an object from file. """
        file_path = os.path.join (os.path.dirname (__file__), "mock", file_name)
        result = None
        with open(file_path) as stream:
            result = json.load (stream)
        return result

    def get_obj_text (self, file_name):
        """ Pretty print an object. """
        return json.dumps (self.get_obj (file_name), indent=2)

class MockMap(MockHelper):
    def __init__(self, requests_mock, test_name):
        super().__init__()
        self.requests_mock = requests_mock
        """ A map of urls to file names of responses. """
        self.mock_map = {
            "predicates": {
                "http://localhost:8099/graph/gamma/predicates" : {
                    "path" : "predicates-1.0.json",
                    "method" : "get"
                },
                "http://localhost:8099/graph/rtx/predicates" : {
                    "path": "rtx_predicates-1.0.json",
                    "method" : "get"
                },
                "http://localhost:8099/clincial/icees/schema" : {
                    "path" : "icees_predicates-1.0.json",
                    "method" : "get"
                },"http://localhost:8099/graph/roger/predicates" : {
                    "path": "rtx_predicates-1.0.json",
                    "method" : "get"
                }
            },
            "workflow-5" : {
                "http://localhost:8099/clinical/cohort/disease_to_chemical_exposure" : {
                    "path" : "disease_to_chemical_exposure-trapi-1.0.json"
                },
                "http://localhost:8099/graph/gamma/quick" : {
                    "path" : "gamma_quick-1.0.json"
                },
                "https://bionames.renci.org/lookup/asthma/disease/" : {
                    "path" : "bionames_asthma_disease.json"
                },
                # "http://localhost:8099/graph/rtx" : {
                #     "path" : "rtx.json"
                # },
            },
            "resolve_name" : {
                "http://mychem.info/v1/query?q=ibuprofen" : {
                    "path" : "mychem_ibuprofen.json",
                    "method" : "get"
                },
                "https://bionames.renci.org/lookup/ibuprofen/chemical_substance/" : {
                    "path" : "bionames_ibuprofen_chemical_substance.json",
                    "method" : "get"
                },
            },
            "automat" : {
                "http://localhost:8099/graph/automat/registry": {
                    "path": "automat-registry.json",
                    "method": "get"
                },
                "http://localhost:8099/graph/automat/viral-proteome/predicates": {
                    "path": "automat-viral-proteome-schema-1.0.json",
                    "method": "get"
                },
                "http://localhost:8099/graph/automat/intact/predicates": {
                    "path": "automat-intact-schema-1.0.json",
                    "method": "get"
                }
            }
        }
        self.load(test_name)
        if test_name != "predicates":
            # Load schema as well, unless the mock map is only being constructed for the schema
            self.load("predicates")

    def load(self, name):
        for k, v in self.mock_map[name].items ():
            method = v['method'] if 'method' in v else 'post'
            text = self.get_obj_text (v['path'])
            if method == 'post':
                self.requests_mock.post (k, text=text)
            elif method == 'get':
                self.requests_mock.get (k, text=text)
            else:
                raise ValueError (f"unknown method {method}")
