import json
import websockets

class MixerWS:

    def __init__(self, url, opts = None):
        self.url = url
        self.opts = opts if opts is not None else dict()

    async def connect(self):
        self.websocket = await websockets.connect(self.url, **self.opts)

    async def send_packet(self, packet):
        packet_raw = json.dumps(packet)
        await self.websocket.send(packet_raw)

    async def receive_packet(self):
        packet_raw = await self.websocket.recv()
        return json.loads(packet_raw)
