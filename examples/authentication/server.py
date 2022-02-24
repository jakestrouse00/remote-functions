from remote_functions import remote, start, Settings

settings = Settings()
settings.authorization = "super_secret_key"


@remote(enforce_types=True, settings=settings)
async def add(a: int, b: int):
    return a + b


if __name__ == '__main__':
    start()
