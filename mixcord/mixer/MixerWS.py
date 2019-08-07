import json
import websockets
import inspect

class MixerWS:

    on_connected = None

    def __init__(self, url, opts = None):
        self.url = url
        self.opts = opts if opts is not None else dict()

    async def try_call(self, func, *opts):
        if inspect.iscoroutinefunction(func):
            await func(*opts)

    async def connect(self):
        self.websocket = await websockets.connect(self.url, **self.opts)
        await self.try_call(self.on_connected)

    async def send_packet(self, packet, retried = False):
        packet_raw = json.dumps(packet)
        await self.websocket.send(packet_raw)

    async def receive_packet(self, retried = False):
        packet_raw = await self.websocket.recv()
        return json.loads(packet_raw)
