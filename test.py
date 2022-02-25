from src.remote_functions import remote, start, Settings, function_manager


class Test1:
    def __init__(self):
        self.k = 1

    # @TestThis
    def add(self, a: int, b: int):
        return a + b

    def multiply(self, a, b):
        return a * b


@remote()
def add(a: int, b: int):
    return a + b


d = Test1()

function_manager.register_multiple_function(d)
# x = Test()
# x.add(1, 2)

# x.add(a=1, b=3)
# @remote(enforce_types=True)
# async def add(a: int, b: int):
#     return a + b


if __name__ == '__main__':
    start(__dev=True)
