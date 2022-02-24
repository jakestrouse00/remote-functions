from remote_functions.interact import Executor

api_url = "http://127.0.0.1:8000"
ex = Executor(api_url, authorization="super_secret_key")

resp = ex.execute("add", a=2, b=3)
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
