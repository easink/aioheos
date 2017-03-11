#!/usr/bin/env python3
" Heos python lib "

import asyncio
import aioheos


@asyncio.coroutine
def heos_test(loop):
    """ test heos """

    verbose = True

    # host = None
    host = 'HEOS-1'
    heos = aioheos.AioHeos(loop, host, verbose=verbose)

    # connect to player
    yield from heos.connect()

    heos.request_play_state()
    heos.request_mute_state()
    heos.request_volume()
    heos.set_volume(10)
    heos.request_groups()

    with open('hello.mp3', mode='rb') as fhello:
        content = fhello.read()
    content_type = 'audio/mpeg'
    heos.play_content(content, content_type)

    # do some work...
    yield from asyncio.sleep(2)

    # close
    heos.close()


def main():
    " main "

    loop = asyncio.get_event_loop()
    heos_task = loop.create_task(heos_test(loop))
    try:
        loop.run_until_complete(heos_task)
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    main()
