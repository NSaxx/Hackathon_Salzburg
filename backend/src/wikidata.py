import requests


def search_wikidata(name: str) -> str | None:
    """Searches the name on Wikidata and returns a matching URL

    Args:
        name: the name that is queried

    Returns:
        Either the URL to the corresponding page or None if there is none
    """
    url = "https://www.wikidata.org/w/api.php"

    headers = {"User-Agent": "UpperAustriaTourism/1.0 (contact@example.at)"}

    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "limit": 10,
    }

    response = requests.get(url, params=params, headers=headers, timeout=15)

    response.raise_for_status()

    result = response.json()["search"]
    print(result)
    if result:
        data_id = result[0]["id"]
        return f"https://www.wikidata.org/entity/{data_id}"
    return None
