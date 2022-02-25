import requests
from typing import List, Union
import pickle
import base64
from dataclasses import dataclass
import codecs


def _get_functions(api_address: str) -> List[str]:
    r = requests.get(api_address + "/functions")
    return r.json()


@dataclass
class Response:
    status_code: int
    exit_code: int
    response: Union[str, dict]

    def __eq__(self, other: int):
        return self.status_code == other


class Executor:
    def __init__(self, api_address: str, authorization: str = ""):
        self.api_address = api_address
        if api_address[-1] == "/":
            self.api_address = api_address[:-1]
        self.authorization = authorization

    def execute(self, function_name: str, **kwargs) -> Response:
        """
        execute a remote function
        :param function_name: name of the function to be executed
        :param kwargs:
        :return Response: response object
        """
        if "/" in function_name:
            # executing function from a class
            splited_function_name = function_name.split("/")
            if len(splited_function_name) != 2:
                raise Exception("function_name only supports two methods")
            class_name = splited_function_name[0]
            func_name = splited_function_name[1]
        else:
            class_name = "main"
            func_name = function_name
        print(f"{self.api_address}/function/{class_name}/{func_name}")
        if function_name not in _get_functions(self.api_address):
            raise Exception(f"{function_name} is not a registered remote function")
        payload = {"args": kwargs}
        headers = {"Authorization": self.authorization}
        r = requests.post(
            f"{self.api_address}/function/{class_name}/{func_name}",
            json=payload,
            headers=headers,
        )

        if r.status_code == 400:
            # there was a forced exception
            response = Response(
                status_code=r.status_code,
                exit_code=r.json()["status"],
                response=r.json()["exception"],
            )

        elif r.status_code == 200:
            # execution was successful
            result = r.json()["result"]
            unencoded_result = pickle.loads(codecs.decode(result.encode(), "base64"))
            response = Response(
                status_code=r.status_code,
                exit_code=r.json()["status"],
                response=unencoded_result,
            )

        elif r.status_code == 500:
            # exception when running the function. Comes with full traceback
            decoded_exception = base64.b64decode(r.json()["exception"]).decode()
            response = Response(
                status_code=r.status_code,
                exit_code=r.json()["status"],
                response=decoded_exception,
            )
        elif r.status_code == 403:
            # execution was forbidden (usually because the authorization was invalid)
            response = Response(
                status_code=r.status_code, exit_code=1, response=r.json()
            )
        elif r.status_code == 404:
            # api path was not found. Something most likely went wrong during registering the api path
            response = Response(
                status_code=r.status_code, exit_code=1, response=r.json()
            )
        else:
            raise Exception(f"Unknown status code: {r.status_code} ")

        return response
