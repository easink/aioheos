#!/usr/bin/env python3
"""Heos python lib."""

import asyncio
import aioheos


@asyncio.coroutine
def heos_test(loop):
    """Test heos."""
    verbose = True
    # host = None
    host = 'HEOS-1'

    heos = aioheos.AioHeosController(loop, host=host, verbose=verbose)

    # connect to player
    yield from heos.connect()

    player_one = heos.get_players()[0]

    player_one.request_update()
    player_one.set_volume(10)
    yield from asyncio.sleep(1)
    print(player_one.volume)

    heos.request_groups()

    # with open('hello.mp3', mode='rb') as fhello:
    #     content = fhello.read()
    # content_type = 'audio/mpeg'
    # player_one.play_content(content, content_type)

    # do some work...
    yield from asyncio.sleep(2)

    heos.close()


def main():
    """Main."""
    loop = asyncio.get_event_loop()
    heos_task = loop.create_task(heos_test(loop))
    try:
        loop.run_until_complete(heos_task)
    except KeyboardInterrupt:
        pass
        # for task in asyncio.Task.all_tasks():
        #     task.cancel()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
