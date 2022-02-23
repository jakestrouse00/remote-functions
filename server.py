from remote_functions.tools import to_api, start


@to_api(enforce_types=False)
def add(a: int, b: int):
    return a + b


start(reload=False)