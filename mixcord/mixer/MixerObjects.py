import json

# https://pastebin.com/KnGGrxde
class MixerUser:

    def __init__(self, data, channel = None):
        self.__dict__.update(**data)
        if isinstance(channel, MixerChannel): self.channel = channel
        else: self.channel = MixerChannel(self.channel, self)

# https://pastebin.com/qD8XNa5i
class MixerChannel:

    def __init__(self, data, user = None):
        self.__dict__.update(**data)
        if isinstance(user, MixerUser): self.user = user
        else: self.user = MixerUser(self.user, self)
