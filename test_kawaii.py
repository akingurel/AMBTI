import json
import requests

with open("config.json", "r") as f:
    config = json.load(f)
    KAWAII_TOKEN = config.get("KAWAII_TOKEN", "anonymous")

sfw_endpoints = [
    "hug", "kiss", "pat", "slap", "cuddle", "poke", "tickle", "feed", "smug", "dance", "blush", "happy", "cry", "angry", "sleep", "laugh", "wave", "wink", "handhold", "highfive", "hold", "nom", "punch", "shoot", "stare", "think", "thumbsup", "wave", "yes", "no", "bite", "bully", "confused", "greet", "kick", "lick", "love", "nervous", "pout", "run", "sad", "scared", "shy", "sick", "smile", "surprised", "tease", "tired", "bored"
]
for ep in sfw_endpoints:
    url = f"https://kawaii.red/api/gif/{ep}?token={KAWAII_TOKEN}"
    r = requests.get(url)
    print(f"Endpoint: {ep}")
    print(r.json())
    print("-"*40) 