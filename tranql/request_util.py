import asyncio
import json
import logging
import aiohttp
import concurrent.futures
import random
from time import time as now
from tranql.exception import ServiceInvocationError, RequestTimeoutError

logger = logging.getLogger (__name__)

async def make_request_async (semaphore, **kwargs):
    response = {}
    errors = []
    timeout = aiohttp.ClientTimeout(total=60*60, connect=None,
                      sock_connect=None, sock_read=None)
    async with aiohttp.ClientSession (timeout=timeout) as session:
        try:
            async with session.request (**kwargs) as http_response:
                # print(f"[{kwargs['method'].upper()}] requesting at url: {kwargs['url']}")
                """ Check status and handle response. """
                if http_response.status == 200 or http_response.status == 202:
                    response = await http_response.json ()
                    #logger.error (f" response: {json.dumps(response, indent=2)}")
                    status = response.get('status', None)
                    if status == "error":
                        raise ServiceInvocationError(
                            f"An error occurred invoking service: {kwargs['url']}.",
                            response['message'])
                    # print (f"** asyncio-response: {json.dumps(response,indent=2)}")
                elif http_response.status == 404:
                    raise UnknownServiceError (f"Service {url} was not found. Is it misspelled?")
                elif http_response.status == 503:
                    raise  ServiceInvocationError(
                        f"An error occurred invoking service: {kwargs['url']}. Returned 503",
                        details= f"Details for the requests:  {kwargs}"
                    )
                else:
                    http_response.raise_for_status()
                    # logger.error (f"error {http_response.status} processing request: {message}")
                # logger.error (http_response.text)
        except concurrent.futures.TimeoutError as e:
            errors.append (RequestTimeoutError(f'Timeout error requesting content from url: "{kwargs.get("url","undefined")}"',kwargs))
        except ServiceInvocationError as e:
            errors.append (e)
        except Exception as e:
            errors.append (e)
    return {
        "response" : response,
        "errors" : errors
    }

"""
Concurrently makes all requests from a given pool of requests

Args:
    requestPool (dict[]): List of **kwarg dictionaries. Keyword arguments will be passed directly to the requests.request call
        Ex: {"method":"post","url":url} => requests.request(method="post",url=url)
    maxRequests (int, optional): Maximum number of requests that may be executing at any given time

Returns:
    Dict containing `responses` and `errors`
"""
def async_make_requests (requestPool, maxRequests=3):

    # Duck test approach
    try:
        loop = asyncio.get_event_loop ()

    except RuntimeError:
        loop = asyncio.new_event_loop ()
        asyncio.set_event_loop (loop)


    semaphore = asyncio.BoundedSemaphore (maxRequests)

    # tasks = asyncio.gather (*[make_request (**request) for request in requestPool])

    tasks = asyncio.gather(*[(make_request_async (semaphore, **request)) for request in requestPool])

    # for request in requestPool:
        # tasks.append (asyncio.ensure_future (make_request (semaphore, **request)))

    results = loop.run_until_complete(tasks)

    responses = []
    errors = []

    for response in results:
        errors.extend (response["errors"])
        if len(response["errors"]) == 0:
            responses.append (response["response"])

    return {
        "responses" : responses,
        "errors" : errors
    }

if __name__ == "__main__":
    reqs = [
        *[
            {
                "method" : "get",
                "url": "https://jsonplaceholder.typicode.com/todos/1",
                "json": {},
                "headers": {
                    'accept': 'application/json'
                }
            }
            for i in range(15)
        ]
    ]

    # Profile time to make all requests asynchronously
    time = now()
    print ("ASYNC REQUESTS:", async_make_requests(reqs))
    # async_make_requests (reqs, 1000)
    print (f"TIME TO COMPLETE {len(reqs)} REQUESTS ASYNCHRONOUSLY:", now() - time)

    import requests
    def make_request_sync (**kwargs):
        response = {}
        unknown_service = False
        try:
            http_response = requests.request (**kwargs)
            """ Check status and handle response. """
            if http_response.status_code == 200 or http_response.status_code == 202:
                response = http_response.json ()
                #logger.error (f" response: {json.dumps(response, indent=2)}")
                status = response.get('status', None)
                if status == "error":
                    raise ServiceInvocationError(
                        message=f"An error occurred invoking service: {url}.",
                        details=truncate(response['message'], max_length=5000))
            elif http_response.status_code == 404:
                unknown_service = True
            else:
                pass
                # logger.error (f"error {http_response.status_code} processing request: {message}")
                # logger.error (http_response.text)
        except ServiceInvocationError as e:
            raise e
        except Exception as e:
            raise e
            # logger.error (f"error performing request: {json.dumps(message, indent=2)} to url: {url}")
            #traceback.print_exc ()
            # logger.error (traceback.format_exc ())
        if unknown_service:
            raise UnknownServiceError (f"Service {url} was not found. Is it misspelled?")
        return response

    # Profile time to make all requests synchronously
    time = now()
    results = []
    for request in reqs:
        results.append (make_request_sync (**request))
    print ("SYNC REQUESTS:", results)
    print (f"TIME TO COMPLETE {len(reqs)} REQUESTS SYNCHRONOUSLY:", now() - time)









#
