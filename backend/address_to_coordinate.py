import requests
import re

standard_url = "https://geocode.at/geocode"

def usable_adddress_converter(address: str) -> dict[str,str]:
    """This function is a helper function to convert standart address notation for austria e.g. Streetname 42, 4242 Place
    into usable format for geocode API to handle"""

    pattern = r"^(?P<street>.+?)\s+(?P<streetNo>\d+[a-zA-Z]?(?:/\d+)?)\s*,\s*(?P<state>\d{4})\s+(?P<city>.+)$"
    
    match = re.match(pattern, address.strip())
    if match:
        data = match.groupdict()
        data["state"] = data["state"][0:1]
        data["streetNo"] = data["streetNo"]
        return data
    else:
        raise ValueError(f"Could not parse address format: '{address}'")

def to_coordinate(usable_address) -> dict[str,str]:
    """takes the object returned by the helper function and turns it into a dictionary holding the latitude and longitude 
    of the respective address"""

    parameters = usable_address

    try:
        respons = requests.get(standard_url, params=parameters, timeout= 10)
        if not respons.ok:
            print(respons.json())

        data = respons.json()
        coordiantes = {"latitude" : data["lat"], "longitude" : data["lng"]}
        return coordiantes

    except requests.exceptions.RequestException as e:
        print(f"errror occured {e}")
        return None


