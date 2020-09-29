import requests
from tranql.exception import ServiceInvocationError

""" How do I add a function?
Adding a function requires two simple steps:
    1) Create said function in a python module (this one is suggested, although not required)
    2) In ufds.yaml, add the name of the function to the `functions` list under the module with
       source "udfs.yaml"

    2.5) If you created the function in a different python module, then here is how to add it to udfs.yaml:
         - Under userDefinedFunctions you should see the `modules` key.
         - Add a new object under modules with keys:
           - source (the file path to the python file, relative to this directory)
           - functions (the functions that should be included from said python module)
"""

""" What can go in and out of UDFs?
Arguments:
    Only supports parsing of any primitive type:
        str,
        int,
        float,
        bool
        e.g. def foo(name: str, count: int, include_similar: bool)

    Also supports nesting function calls
        e.g. def foo(curie),
             where gene=foo(resolve_curie("asthma"))

    Supports keyword/optional arguments
        e.g. def foo(a, b, c=True),
             where gene=foo("x", "y")

Outputs:
    Supports any return type, although the end product should
    return a type which is compatible with whatever field it is for.
        For example, in the statement `where gene=foo("x")` foo should
        return either a string or a list of strings; gene can't be an int/boolean for example
        However, something like an ICEES field may be an integer rather than a string

    Also, since function nesting is supported, list arguments are weakly suppported.
    A function argument may be a list, but the only way to then use the function is
    to pass in a function call as the argument that returns a list.
        For example: def takes_a_list(list_arg); def returns_list(): return ["MONDO:X", "MONDO:Y"]
                     where gene=takes_a_list(returns_list())
"""


""" Ontological functions invoking the ONTO API """
def make_onto_request(url):
    response = requests.get(
        url,
        headers = {'accept': 'application/json'}
    )
    if response.ok:
        return response.json()
    else:
        raise ServiceInvocationError(response.text)
def filter_onto(results):
    """ Make sure the only thing in the results are curies. ONTO also returns stuff like owl#Thing """
    filtered = []
    for result in results:
        if not result.startswith("http://") and not result.startswith("https://"):
            filtered.append(result)
    return filtered
def children(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/children/{curie}"))
def descendants(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/descendants/{curie}"))
def ancestors(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/ancestors/{curie}"))
def parents(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/parents/{curie}")).get("parents", [])
def siblings(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/siblings/{curie}")).get("siblings", [])
def close_match(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/closeMatch/{curie}").get("close matches", []))
def exact_match(curie):
    return filter_onto(make_onto_request(f"https://onto.renci.org/exactMatch/{curie}").get("exact matches", []))

""" Logic functions/operators. Not any practical usage currently. """
def AND(a, b):
    return a and b
def OR(a, b):
    return a or b
def XOR(a, b):
    return a ^ b
