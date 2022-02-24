from src.tools import remote, start, Settings


@remote(enforce_types=True)
async def add(a: int, b: int):
    return a + b


if __name__ == '__main__':
    start()
