from remote_functions.interact import Executor

ex = Executor("http://127.0.0.1:8000")

resp = ex.execute("test", i=5)
print(resp.response)

