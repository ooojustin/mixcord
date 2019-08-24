from _2captcha import _2Captcha
from syncer import sync
import requests, json, sys

# TODO: the mixer module will *eventually* be installed via pypi
# i am temporarily spcifying the path during development of the wrapper
sys.path.append(R"C:\Users\justi\Documents\Programming\mixer.py")
from mixer.api import MixerAPI
from mixer.oauth import MixerOAuth

# load settings
settings_raw = open("./oauth-token-gen/settings.cfg").read()
settings = json.loads(settings_raw)

# initialize 2captcha
key = settings["2captcha"]
client = _2Captcha(key)

# get valid mixer token
print("getting valid recaptcha token...")
sitekey = "6LeYS2gUAAAAAPVr3SzjSJYtfD7iBxS5yyWS0IuH"
pageurl = "https://mixer.com/"
recaptcha = client.recaptcha2(sitekey, pageurl)
token = recaptcha.solve()

# create mixer session and login
print("establishing login session cookies...")
session = requests.Session()
url = "https://mixer.com/api/v1/users/login"
data = {
    "username": settings["email"],
    "password": settings["password"],
    "captcha": token
}
response = session.post(url, data)
assert response.status_code == 200, f"Mixer login failed: {response.text}"

# get jwt from authorize endpoint
print("retrieving jwt from authorize endpoint...")
url = "https://mixer.com/api/v1/jwt/authorize"
response = session.post(url)
jwt = response.headers.get("x-jwt")
assert jwt, f"Failed to get JWT. (status code: {response.status_code})"

# all possible scopes
scope = [
"user:act_as", "achievement:view:self", "channel:analytics:self",
"channel:clip:create:self", "channel:clip:delete:self", "channel:costream:self",
"channel:deleteBanner:self", "channel:details:self", "channel:follow:self",
"channel:streamKey:self", "channel:teststream:view:self", "channel:update:self",
"chat:bypass_catbot", "chat:bypass_filter", "chat:bypass_links",
"chat:bypass_slowchat", "chat:cancel_skill", "chat:change_ban",
"chat:change_role", "chat:chat", "chat:clear_messages",
"chat:connect", "chat:edit_options", "chat:giveaway_start",
"chat:poll_start", "chat:poll_vote", "chat:purge",
"chat:remove_message", "chat:timeout", "chat:view_deleted",
"chat:whisper", "delve:view:self", "interactive:manage:self",
"interactive:robot:self", "invoice:view:self", "log:view:self",
"oauth:manage:self", "recording:manage:self", "redeemable:create:self",
"redeemable:redeem:self", "redeemable:view:self", "resource:find:self",
"subscription:cancel:self", "subscription:create:self", "subscription:renew:self",
"subscription:view:self", "team:manage:self", "transaction:cancel:self",
"transaction:view:self", "user:analytics:self", "user:details:self",
"user:getDiscordInvite:self", "user:log:self", "user:notification:self",
"user:seen:self", "user:update:self", "user:updatePassword:self"
]

async def generate_shortcode():
    print("generating shortcode oauth handle...")
    data = await api.get_shortcode(scope)
    return data.get("code"), data.get("handle")

async def resolve_tokens():

    # get code to generate oauth tokens
    print("verifying authorization...")
    data = await api.check_shortcode(handle)
    code = data.get("code")
    assert code, "Failed to get authorization code."

    # automatically generate oauth tokens
    global oauth
    oauth = await MixerOAuth.create_from_authorization_code(api, code)
    print("acquired tokens, expires:", oauth.expires)
    # NOTE: oauth.access_token + oauth.refresh_token are defined!

    # close aiohttp session
    await api.close()

# initialize api
api = MixerAPI(settings["client-id"], settings["client-secret"])

# generate shortcode oauth process info
code, handle = sync(generate_shortcode())

# authorize it with our previously generated jwt :)
print("authorizing...")
url = f"https://mixer.com/api/v1/oauth/shortcode/activate/{code}"
session.post(url, headers = { "Authorization": f"JWT {jwt}"})

# confirm authorization and get tokens
sync(resolve_tokens())

print("completed!")
# print(oauth.access_token, oauth.refresh_token)
