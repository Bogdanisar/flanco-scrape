import requests
import json
import sys

host = 'localhost'
url = f"http://{host}:4444/wd/hub/status"

try:
    req = requests.get(url)
    print(json.loads(req.text)['value']['ready'])
except:
    print("Got exceptions!\n\n")
    raise
