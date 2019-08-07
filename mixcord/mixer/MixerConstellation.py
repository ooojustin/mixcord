from .MixerWS import MixerWS

class MixerConstellation:

    CONSTELLATION_URL = "wss://constellation.mixer.com"
    websocket = None

    def __init__(self, on_connected):
        self.on_connected = on_connected
        self.callbacks = dict()
        self.packet_id = 0

    async def connect(self, *args):
        opts = { "extra_headers": { "Authorization": "Bearer " + self.oauth.access_token } }
        self.reconnected = self.websocket is not None
        self.websocket = MixerWS(self.CONSTELLATION_URL, opts)
        await self.websocket.connect()
        await self.on_connected(self) # call on_connected func (we should probably subscribe to events)

    async def start(self, oauth):

        self.oauth = oauth
        self.oauth.refreshed_events.append(self.connect)
        await self.connect()

        while True:

            # receive a packet from server
            try:
                packet = await self.websocket.receive_packet()
            except: pass

            # ignore the first packet if we just reconnected
            # this is because we were still awaiting a recv() call in the old websocket object
            if self.reconnected:
                self.reconnected = False
                continue

            # make sure it's an event we're subscribed to
            if packet["type"] != "event": continue
            if packet["event"] != "live": continue

            # find and invoke the callback function with the packet & payload
            event_name = packet["data"]["channel"]
            payload = packet["data"]["payload"]
            callback = self.callbacks.get(event_name, None)
            if callback is not None:
                await callback(packet, payload)

    async def subscribe(self, events, callback):

        # if a single event is provided, wrap it in a list automatically
        if isinstance(events, str):
            events = [events]

        # build livesubscribe packet
        packet = {
            "type": "method",
            "method": "livesubscribe",
            "params": {
                "events": events
            },
            "id": self.packet_id
        }

        # send packet to server and determine callback
        await self.websocket.send_packet(packet)
        for event in events:
            self.callbacks[event] = callback

        # increment packet id and return unique packet id
        self.packet_id += 1
        return self.packet_id
