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
    def __init__(self, api_address: str):
        self.api_address = api_address
        if api_address[-1] == "/":
            self.api_address = api_address[:-1]

    def execute(self, function_name: str, **kwargs) -> Response:
        """
        execute a remote function
        :param function_name: name of the function to be executed
        :param kwargs:
        :return Response: response object
        """
        if function_name not in _get_functions(self.api_address):
            raise Exception(f"{function_name} is not a registered remote function")
        payload = {"args": kwargs}
        r = requests.post(f"{self.api_address}/functions/{function_name}", json=payload)

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
        else:
            raise Exception("Response is malformed")

        return response


if __name__ == "__main__":
    x = Executor("http://127.0.0.1:8000")
    # x.execute("test", m="dude")
