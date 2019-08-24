import requests
import time
class RecaptchaV2:

    def __init__(self, client, id):
        self.client = client
        self.id = id

    def check(self):
        return self.client._check(self.id)

    def solve(self):
        loops = 0
        time.sleep(15)
        while loops < 10:
            loops += 1
            time.sleep(5)
            data = self.check()
            request = data.get("request")
            if data.get("status"):
                return request
            assert request == "CAPCHA_NOT_READY", f"Unexpected 'request': {request}"
        raise Exception("Request timed out.")

class _2Captcha:

    url = "https://2captcha.com/{}.php"

    def __init__(self, key):
        self.key = key

    def post(self, file, data):
        data["key"] = self.key
        data["json"] = 1
        response = requests.post(self.url.format(file), data)
        return response.json()

    def recaptcha2(self, sitekey, url):
        data = {
            "method": "userrecaptcha",
            "googlekey": sitekey,
            "pageurl": url
        }
        response = self.post("in", data)
        id = response.get("request")
        return RecaptchaV2(self, id) if id else None

    def _check(self, id):
        data = {
            "action": "get",
            "id": id
        }
        return self.post("res", data)
