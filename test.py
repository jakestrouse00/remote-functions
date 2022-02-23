from remote_functions.tools import to_api, start


@to_api(enforce_types=True)
def test(i: int):
    return i / 0


start(reload=False)

