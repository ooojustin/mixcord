from _2captcha import _2Captcha
import requests, json

# load settings
settings_raw = open("./test/settings.cfg").read()
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

print("generating shortcode oauth handle...")
# TODO: generate shortcode oauth?

# authorize it :)
print("authorizing...")
url = f"https://mixer.com/api/v1/oauth/shortcode/activate/{code}"
session.post(url, headers = { "Authorization": f"JWT {jwt}"})

print("polling to verify authorization...")
# TODO: get authorization code

print("retrieving tokens...")
# TODO: initialize MixerOAuth

print("completed!")
