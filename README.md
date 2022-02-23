# remote-functions


## Requirements

Python 3.8+

## Installation

<div class="termy">

```console
$ pip install remote-functions
```

</div>

## Example

### Server side

* Create a file `server.py` with:

```Python
from remote_functions.tools import to_api, start


@to_api(enforce_types=False)
def add(a: int, b: int):
    return a + b


start(reload=False)

```


### Client side

* Create a file `client.py` with:

```Python
from remote_functions.interact import Executor

api_url = "http://127.0.0.1:8000"
ex = Executor(api_url)

resp = ex.execute("add", a=2, b=3)
if resp.exit_code == 0:
    # function executed successfully
    print(resp.response)  # 5
elif resp.exit_code == 1:
    # function arguments are malformed
    print(resp.response)
elif resp.exit_code == 2:
    # function has an exception
    print(resp.response)  # gives us the full traceback for easy debugging

```