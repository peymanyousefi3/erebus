"""Expose only the R2025a external-controller transport; never HTTP or WebSocket.

The Webots backend MUST be on an organizer-only network. This gateway does not
make a separately exposed Webots port private.
"""
import argparse
import asyncio
import struct


async def relay(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()
    if writer.can_write_eof():
        writer.write_eof()


async def robot_requests(reader, writer):
    # R2025a requests start with a little-endian total packet size. Preserve
    # their bytes, but never let an HTTP upgrade follow a controller handshake.
    while True:
        header = await reader.readexactly(4)
        size = struct.unpack('<I', header)[0]
        if size != 0 and not 8 <= size <= 64 * 1024 * 1024:
            raise ValueError('Invalid controller frame')
        writer.write(header)
        await writer.drain()
        if size == 0:
            return
        remaining = size - 4
        while remaining:
            data = await reader.readexactly(min(remaining, 65536))
            writer.write(data)
            await writer.drain()
            remaining -= len(data)


async def controller(client, reply, host, port, robot):
    backend = None
    try:
        # R2025a scheduler.c sends this exact preamble with --robot-name.
        # A validated connection is permanently handed to the robot controller
        # by Webots, so subsequent bytes cannot become browser requests.
        header = b'CTR\nRobot-Name: ' + robot.encode('ascii')
        prefix = await asyncio.wait_for(client.readexactly(3), 5)
        if prefix != b'CTR':
            return
        received = prefix + await asyncio.wait_for(client.readexactly(len(header)-3), 5)
        if received != header:
            return
        reader, backend = await asyncio.wait_for(asyncio.open_connection(host, port), 5)
        backend.write(header)
        await backend.drain()
        await asyncio.gather(robot_requests(client, backend), relay(reader, reply))
    except (OSError, ValueError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        pass
    finally:
        for writer in (backend, reply):
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass


async def serve(host, port, backend_host, backend_port, robot):
    if not robot.isascii() or not robot.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Use the encoded participant robot name, without scene syntax.')
    server = await asyncio.start_server(
        lambda r, w: controller(r, w, backend_host, backend_port, robot), host, port)
    print(f'Controller-only gateway listening on {host}:{port}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--listen', default='127.0.0.1')
    p.add_argument('--port', type=int, default=1234)
    p.add_argument('--backend', default='127.0.0.1')
    p.add_argument('--backend-port', type=int, default=1255)
    p.add_argument('--robot', default='Erebus_Bot')
    a = p.parse_args()
    asyncio.run(serve(a.listen, a.port, a.backend, a.backend_port, a.robot))
