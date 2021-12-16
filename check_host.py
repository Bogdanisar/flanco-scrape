import requests
import json

host = 'localhost'
url = f"http://{host}:4444/wd/hub/status"

req = requests.get(url)
print(json.loads(req.text)['value']['ready'])
