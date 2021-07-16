
class GraphInterfaceMock():
    def __init__(self):
        pass
    def get_schema(self):
        return {
            "biolink:ChemicalSubstance": {
                "biolink:Gene": [
                    "biolink:intracts_with"
                ]
            }
        }