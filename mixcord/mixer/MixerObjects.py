import json

# https://pastebin.com/KnGGrxde
class MixerUser:

    api = None

    def __init__(self, data, channel = None):
        self.__dict__.update(**data)
        if isinstance(channel, MixerChannel): self.channel = channel
        else: self.channel = MixerChannel(self.channel, self)

# https://pastebin.com/qD8XNa5i
class MixerChannel:

    api = None

    def __init__(self, data, user = None):
        self.__dict__.update(**data)
        if isinstance(user, MixerUser): self.user = user
        else: self.user = MixerUser(self.user, self)

    def get_broadcast(self):
        return self.api.get_broadcast(self.id)

    def get_uptime(self):
        return self.api.get_uptime(self.id)

    def get_leaderboard(self, type, limit = 10):
        return self.api.get_leaderboard(type, self.id, limit)
