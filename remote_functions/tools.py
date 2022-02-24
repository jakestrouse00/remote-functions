from fastapi import FastAPI, Response, status, Request, Depends
from starlette.exceptions import HTTPException as StarletteHTTPException
from dataclasses import dataclass
from typing import Optional, Tuple, get_type_hints, List, Dict, Any
from pydantic import BaseModel
import uvicorn
import codecs
import traceback
import inspect
import base64
import pickle

"""
internal status codes:
0 = successful execution
1 = failed execution (example: missing arguments for the function)
2 = exception raised by the function being executed. This will be accompanied by the full traceback
"""

"""todo:
add ability to check if passed function is async. If it is async, use a fastapi path with async
"""

app = FastAPI(docs_url=None, redoc_url=None)

registered_functions = []


class HTTPException(StarletteHTTPException):
    def __init__(
            self,
            status_code: int,
            error_code: int,
            detail: Any = None,
            fields: List[Dict] = None,
    ) -> None:
        """
        Generic HTTP Exception with support for custom status & error codes.
        :param status_code: HTTP status code of the response
        :param error_code: Custom error code, unique throughout the app
        :param detail: detailed message of the error
        :param fields: list of dicts with key as field and value as message
        """
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.fields = fields or []


@app.get("/functions")
def get_functions():
    return registered_functions


@dataclass
class Settings:
    authorization: str = None


class _AuthHolder:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _check_authorization(self, request: Request):
        if self.settings is None or self.settings.authorization is None:
            return True
        if not request.headers.get("authorization") == self.settings.authorization:
            error_msg = "Forbidden."
            status_code = status.HTTP_403_FORBIDDEN
            error_code = status.HTTP_403_FORBIDDEN
            raise HTTPException(
                status_code=status_code,
                detail=error_msg,
                error_code=error_code
            )
        else:
            return True


@dataclass
class _Check:
    invalid: bool
    response: dict = None


class _PostData(BaseModel):
    args: Optional[dict] = None


def remote(enforce_types: bool = False, settings: Settings = None):
    def remote_inside(func):
        if func.__name__ not in registered_functions:
            registered_functions.append(func.__name__)
        else:
            # function is already defined
            raise Exception(
                f"A function with the name {func.__name__} has already been defined"
            )

        holder = _AuthHolder(settings)
        function_is_async = inspect.iscoroutinefunction(func)

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
                joined = joined.replace("     ", ", ")
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

        @app.post(f"/functions/{func.__name__}", dependencies=[Depends(holder._check_authorization)])
        async def wrap(data: _PostData, response: Response):
            args = inspect.getfullargspec(func).args
            if len(args) > 0:
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
                if data.args is None:
                    func_args = {}
                else:
                    func_args = data.args
                if function_is_async:
                    result = await func(**func_args)
                else:
                    result = func(**func_args)
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

    return remote_inside


def start(host: str = "127.0.0.1", port: int = 8000, reload: bool = False, **kwargs):
    uvicorn.run("remote_functions.tools:app", host=host, port=port, reload=reload, **kwargs)
