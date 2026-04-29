import requests

url = "https://24data.ptfs.app/acft-data"


response = requests.get(url)

data = response.json()

id = "JondoOnaca"

for code in data:
    if id == data[code]["playerName"]:
        print(data[code])
        print(data[code]["position"])
        break