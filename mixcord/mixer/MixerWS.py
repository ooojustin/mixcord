import json
import websockets

class MixerWS:

    def __init__(self, url, opts = None):
        self.url = url
        self.opts = opts if opts is not None else dict()
        self.on_connected = None

    async def connect(self):
        self.websocket = await websockets.connect(self.url, **self.opts)
        if self.on_connected is not None:
            await self.on_connected()

    async def send_packet(self, packet, retried = False):
        try:
            packet_raw = json.dumps(packet)
            await self.websocket.send(packet_raw)
        except websockets.exceptions.ConnectionClosed:
            if not retried:
                print("reconnecting in send_packet...")
                self.connect()
                self.send_packet(packet, True)

    async def receive_packet(self, retried = False):
        try:
            packet_raw = await self.websocket.recv()
            return json.loads(packet_raw)
        except websockets.exceptions.ConnectionClosed:
            if not retried:
                print("reconnecting in receive_packet...")
                self.connect()
                self.receive_packet(True)
