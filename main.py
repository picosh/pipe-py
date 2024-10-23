import asyncio
import datetime

import pipe_py


async def main():
    pc = pipe_py.PipeClient(
        "pipe.pico.sh", 22, "keyfile"
    )

    async def pipe():
        a = await pc.pipe("foobar3")

        while True:
            data = await a.read()
            await a.write(f"PIPE: {data}")
            print(f"Echoing data: {data}")

    async def sub():
        a = await pc.sub("foobar2")

        while not a.read_done():
            data = await a.read()
            print(f"Read data: {data}")

    async def pub():
        a = await pc.pub("foobar")

        while True:
            current_time = datetime.datetime.now()
            await a.write(f"PUB: {current_time}\n")

            print(f"Write data: {current_time}")
            await asyncio.sleep(1)

    await asyncio.gather(pipe(), sub(), pub(), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
