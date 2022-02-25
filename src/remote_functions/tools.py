from fastapi import FastAPI, Response, status, Request, Depends, APIRouter
import warnings
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

registered_functions = []

"""
internal status codes:
0 = successful execution
1 = failed execution (example: missing arguments for the function)
2 = exception raised by the function being executed. This will be accompanied by the full traceback
"""

"""todo:
Make decorator be able to be used on a class and then create function paths for each function in the class
"""

app = FastAPI(docs_url=None, redoc_url=None)
router = APIRouter()


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
    return function_manager.list_functions()


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


@dataclass
class Function:
    callback_function: Any
    parent_class_name: str

    def __post_init__(self):
        self.parent_class_name = self.parent_class_name.lower()
        self.function_path = f"{self.parent_class_name.lower()}/{self.callback_function.__name__.lower()}"

    def __eq__(self, other):
        return other == self.function_path

    def __hash__(self):
        return hash(self.function_path)


class Functions:
    def __init__(self):
        self.functions: List[Function] = []

    def register_function(self, callback_function: object, enforce_types: bool = False, settings: Settings = None) -> Function:
        """
        registers a function
        :param settings:
        :param enforce_types:
        :param callback_function:
        :return:
        True if function has been registered
        False if function already exists
        """
        if len(str(callback_function.__qualname__).split(".")) == 1:
            # function is not located inside an object
            parent_class_name = "main"
        else:
            # function is part of an object
            parent_class_name = str(callback_function.__qualname__).split(".")[0]
        func = Function(callback_function, parent_class_name)
        if func not in self.functions:
            self.functions.append(func)
            register_api_path(func, enforce_types=enforce_types, settings=settings)
            return func
        else:
            warnings.warn(f"Function is already registered: {func.function_path}")

    def register_multiple_functions(self, input_object: object, enforce_types: bool = False, settings: Settings = None) -> List[Function]:
        results = []
        for name, function_exec in inspect.getmembers(input_object,
                                                      lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
            if name != "__init__":
                function_obj = Function(function_exec, input_object.__class__.__name__)
                if function_obj not in self.functions:
                    self.functions.append(function_obj)
                    register_api_path(function_obj, enforce_types=enforce_types, settings=settings)
                    results.append(function_obj)
                else:
                    warnings.warn(f"Function is already registered: {function_obj.function_path}")
        return results

    def find_function(self, function_path: str) -> Function:
        filtered_functions = list((filter(lambda x: x == function_path, self.functions)))
        if len(filtered_functions) != 0:
            return filtered_functions[0]

    def list_functions(self):
        all_functions = list(map(lambda x: x.function_path, self.functions))
        return all_functions


function_manager = Functions()


class _PostData(BaseModel):
    args: Optional[dict] = None


async def _arguments_missing(data: _PostData, stored_function_callback) -> _Check:
    """
    check if all required arguments are present
    :param data: post data
    :return _Check object:
    _Check.invalid == True if arguments have incorrect types
    """
    # I can just call registered_function.callback_function directly, but it may cause issues
    # may want to use function_manager.find() with the path if there are issues
    args = inspect.getfullargspec(stored_function_callback).args
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
                "exception": f"TypeError: {stored_function_callback.__name__}() missing {len(missing_args)} required positional arguments: {joined}",
            },
        )


async def _arguments_correct_type(data: _PostData, stored_function_callback) -> _Check:
    """
    checks if all arguments have the correct types
    :param data: post data
    :return _Check object:
    _Check.invalid == True if arguments have incorrect types
    """
    args = data.args
    hints = get_type_hints(stored_function_callback)
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
                "exception": f"TypeError: {stored_function_callback.__name__}() incorrect types: {joined}",
            },
        )


def register_api_path(function: Function, enforce_types: bool, settings: Settings = None):
    print(f"registered_api_path: {function.function_path}")
    func_path = function.function_path

    holder = _AuthHolder(settings)
    function_is_async = inspect.iscoroutinefunction(function.callback_function)

    @app.post(f"/function/{func_path}", dependencies=[Depends(holder._check_authorization)])
    async def wrap(data: _PostData, response: Response, request: Request):
        function_path = "/".join(request.url.path.split("/")[2:])
        stored_function = function_manager.find_function(function_path)
        stored_function_callback = stored_function.callback_function
        args = inspect.getfullargspec(stored_function_callback).args
        if len(args) > 0:
            # arguments are required
            arg_check = await _arguments_missing(data, stored_function_callback)
            if arg_check.invalid:
                # there are arguments missing
                response.status_code = status.HTTP_400_BAD_REQUEST
                return arg_check.response
            else:
                # no arguments missing
                pass

            if enforce_types:
                type_check = await _arguments_correct_type(data, stored_function_callback)
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
                result = await stored_function_callback(**func_args)
            else:
                result = stored_function_callback(**func_args)
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


def remote(enforce_types: bool = False, settings: Settings = None):
    def remote_inside(func):
        # automatically registers the api path
        registered_function = function_manager.register_function(func, enforce_types=enforce_types, settings=settings)

    return remote_inside


def start(host: str = "127.0.0.1", port: int = 8000, reload: bool = False, __dev: bool = False, **kwargs):
    if not __dev:
        uvicorn.run("remote_functions.tools:app", host=host, port=port, reload=reload, **kwargs)
    else:
        uvicorn.run("src.remote_functions.tools:app", host=host, port=port, reload=reload, **kwargs)
