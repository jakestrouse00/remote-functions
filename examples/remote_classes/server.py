from remote_functions import remote, start, functions_manager


class SampleRemoteClass:
    def __init__(self):
        self.a = 5

    def increase(self, count: int):
        self.a += count
        return self.a


# first we have to initialize the class
initialized_class = SampleRemoteClass()
# now we manually register the entire class
functions_manager.register_multiple_functions(initialized_class, enforce_types=False)
# you can also register each function in the class individually. In case you want to do something like only enforcing type hints on some functions
# to register a single function you would do:
functions_manager.register_function(initialized_class.increase, enforce_types=True)


if __name__ == '__main__':
    start()
