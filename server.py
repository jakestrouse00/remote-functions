from remote_functions.tools import remote, start


@remote(enforce_types=False)
def add(a: int, b: int):
    return a + b


start(reload=False)