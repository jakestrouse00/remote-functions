from fastapi import FastAPI, Response, status
from dataclasses import dataclass
from typing import Optional, Tuple, get_type_hints
from pydantic import BaseModel
import uvicorn
import codecs
import traceback
import inspect
import base64
import pickle

"""
internal status code notes:
0 = successful execution
1 = failed execution (example: missing arguments for the function)
2 = exception raised by the function being executed. This will be accompanied by the full traceback
"""

app = FastAPI(docs_url=None, redoc_url=None)

all_paths = []


@app.get("/functions")
def get_functions():
    return all_paths


@dataclass
class _Check:
    invalid: bool
    response: dict = None


class _PostData(BaseModel):
    args: Optional[dict] = None


def to_api(enforce_types: bool = False):
    def to_api_inside(func):
        if func.__name__ not in all_paths:
            all_paths.append(func.__name__)
        else:
            # function is already defined
            raise Exception(
                f"A function with the name {func.__name__} has already been defined"
            )

        def _arguments_missing(data: _PostData) -> _Check:
            """
            check if all required arguments are present
            :param data: post data
            :return _Check object:
            _Check.invalid == True if arguments have incorrect types
            """
            args = inspect.getfullargspec(func).args
            missing_args = []
            for arg in args:
                if arg not in data.args.keys():
                    missing_args.append(f"'{arg}'")
            if len(missing_args) == 0:
                return _Check(invalid=False)
            else:
                joined = "     ".join(missing_args)
                joined.replace("     ", " and ")
                return _Check(
                    invalid=True,
                    response={
                        "status": 1,
                        "exception": f"TypeError: {func.__name__}() missing {len(missing_args)} required positional arguments: {joined}",
                    },
                )

        def _arguments_correct_type(data: _PostData) -> _Check:
            """
            checks if all arguments have the correct types
            :param data: post data
            :return _Check object:
            _Check.invalid == True if arguments have incorrect types
            """
            args = data.args
            hints = get_type_hints(func)
            incorrect_types = []
            for arg in args.keys():
                if type(data.args[arg]) != hints[arg]:
                    incorrect_types.append(f"'{arg}' requires {hints[arg]}")
            if len(incorrect_types) == 0:
                return _Check(invalid=False)
            else:
                joined = ", ".join(incorrect_types)
                return _Check(
                    invalid=True,
                    response={
                        "status": 1,
                        "exception": f"TypeError: {func.__name__}() incorrect types: {joined}",
                    },
                )

        @app.post(f"/functions/{func.__name__}")
        def wrap(data: _PostData, response: Response):
            args = inspect.getfullargspec(func).args
            if len(args) == 0:
                # no arguments for the function
                try:
                    result = func()
                except:
                    error_info = traceback.format_exc()
                    encoded_error = base64.b64encode(
                        error_info.encode("ascii")
                    ).decode()
                    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    return {
                        "status": 2,
                        "exception": encoded_error,
                    }
            else:
                # arguments are required
                arg_check = _arguments_missing(data)
                if arg_check.invalid:
                    # there are arguments missing
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return arg_check.response
                else:
                    # no arguments missing
                    pass

                if enforce_types:
                    type_check = _arguments_correct_type(data)
                    if type_check.invalid:
                        # arguments have wrong types
                        response.status_code = status.HTTP_400_BAD_REQUEST
                        return type_check.response
                    else:
                        # all arguments have correct types
                        pass
                try:
                    result = func(**data.args)
                except:
                    error_info = traceback.format_exc()
                    encoded_error = base64.b64encode(
                        error_info.encode("ascii")
                    ).decode()
                    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    return {
                        "status": 2,
                        "exception": encoded_error,
                    }

            pickled_result = codecs.encode(pickle.dumps(result), "base64").decode()
            response.status_code = status.HTTP_200_OK
            return {"status": 0, "result": pickled_result}

        return wrap

    return to_api_inside


def start(**kwargs):
    uvicorn.run("remote_functions.tools:app", **kwargs)
