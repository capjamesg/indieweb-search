import requests

def verify(headers, session):
    if headers.get("Authorization") is not None:
        access_token = headers.get("Authorization").split(" ")[-1]
    elif session.get("access_token"):
        access_token = session.get("access_token")
    else:
        return False

    request = requests.get(
        session.get("token_endpoint"), headers={"Authorization": "Bearer " + access_token}
    )

    if request.status_code != 200 or (
        request.json().get("me") and request.json()["me"].strip("/") != ME.strip("/")
    ):
        return False

    return True