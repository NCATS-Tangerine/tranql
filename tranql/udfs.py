import requests
from tranql.exception import ServiceInvocationError

def children(curie):
    response = requests.get(
        f"https://onto.renci.org/children/{curie}",
        headers = {'accept': 'application/json'}
    )
    if response.ok:
        return response.json()
    else:
        raise ServiceInvocationError(response.text)
