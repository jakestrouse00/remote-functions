from remote_functions import Executor

api_url = "http://127.0.0.1:8000"
ex = Executor(api_url)

# the class name and function name are automatically converted to lower case when the api path is registered
resp = ex.execute("sampleremoteclass/increase", count=2)
print(resp)
if resp.exit_code == 0:
    # function executed successfully
    print(resp.response)  # 5
elif resp.exit_code == 1:
    # function arguments are malformed
    pass
elif resp.exit_code == 2:
    # function has an exception
    print(resp.response)  # gives us the full traceback for easy debugging
