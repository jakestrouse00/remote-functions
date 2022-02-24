# remote-functions

---
Remote-functions provides type enforced remotely run Python functions. Using remote-functions,
developers can run Python functions from any device with any programming language.


### Key Features
* **Fast**: Built on top of [FastAPI](https://github.com/tiangolo/fastapi).
* **Easy**: Designed to be easy to use and learn.
* **Type Checking**: Built-in type checking for function arguments.


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
from remote_functions.tools import remote, start


@remote(enforce_types=True)
def add(a: int, b: int):
    return a + b

if __name__ == '__main__':   
    start()

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
    # function arguments were malformed
    print(resp.response)
elif resp.exit_code == 2:
    # function had an exception during execution
    print(resp.response)  # gives us the full traceback for easy debugging

```

## Run it
First start the server with:
<div class="termy">

```console
$ python server.py
```

</div>

Then run client.py to test your remote function

<div class="termy">

```console
$ python client.py
```

</div>

<details markdown="1">
<summary><b>Deploy in production</b></summary>

To deploy your application for production you just have to slightly modify your server.py file

```Python
from remote_functions.tools import remote, start


@remote(enforce_types=True)
def add(a: int, b: int):
    return a + b


if __name__ == '__main__':
    start(host="0.0.0.0", port=80)
```
</details>

## License

This project is licensed under the terms of the MIT license.