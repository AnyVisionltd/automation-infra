import requests


def external_ip():
    return requests.get("http://checkip.amazonaws.com/").text.strip()