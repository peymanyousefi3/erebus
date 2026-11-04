"""The public transport must reject browser requests and preserve robot bytes."""
import asyncio
import struct
import importlib.util
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gateway',root/'scripts/controller_gateway.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

async def check():
    seen=[];header=b'CTR\nRobot-Name: Erebus_Bot'
    async def backend(reader,writer):
        try:
            seen.append(await reader.readexactly(len(header)))
            writer.write(b'CONNECTED');await writer.drain()
            await g.relay(reader,writer)
        except OSError:
            pass
        finally:
            writer.close()
            try:await writer.wait_closed()
            except OSError:pass
    private=await asyncio.start_server(backend,'127.0.0.1',0);port=private.sockets[0].getsockname()[1]
    public=await asyncio.start_server(lambda r,w:g.controller(r,w,'127.0.0.1',port,'Erebus_Bot'),'127.0.0.1',0);gateway=public.sockets[0].getsockname()[1]
    try:
        for request in (b'GET /robot_windows/MainSupervisorWindow/thumbnails/world4.png HTTP/1.1\r\n\r\n',b'GET / HTTP/1.1\r\nUpgrade: websocket\r\n\r\n',b'CTR\nRobot-Name: MAINSUPERVISOR',b'CTR\nRobot-Name: Other_Robot'):
            reader,writer=await asyncio.open_connection('127.0.0.1',gateway);writer.write(request);await writer.drain()
            try:answer=await asyncio.wait_for(reader.read(),1)
            except ConnectionResetError:answer=b''
            assert answer==b'' and seen==[],(answer,seen)
            writer.close()
        reader,writer=await asyncio.open_connection('127.0.0.1',gateway)
        for part in (header[:1],header[1:7],header[7:]):writer.write(part);await writer.drain();await asyncio.sleep(.01)
        assert await reader.readexactly(9)==b'CONNECTED'
        data=bytes(range(256))*4096
        payload=struct.pack('<I',len(data)+4)+data
        writer.write(payload);await writer.drain()
        assert await reader.readexactly(len(payload))==payload
        assert seen==[header]
        writer.close();await writer.wait_closed()
        # A second browser handshake cannot be smuggled into a valid session.
        reader,writer=await asyncio.open_connection('127.0.0.1',gateway)
        writer.write(header+b'GET / HTTP/1.1\r\nUpgrade: websocket\r\n\r\n');await writer.drain()
        answer=await asyncio.wait_for(reader.read(),1)
        assert answer in (b'',b'CONNECTED'),answer
        writer.close();await writer.wait_closed()
    finally:
        public.close();private.close();await public.wait_closed();await private.wait_closed()
asyncio.run(check())
print('PASS: HTTP/WebSocket/privileged-robot rejection, fragmented handshake and exact 1 MiB robot transport.')
