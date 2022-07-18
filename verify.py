import requests


def verify(headers, session):
    if headers.get("Authorization") is not None:
        access_token = headers.get("Authorization").split(" ")[-1]
    elif session.get("access_token"):
        access_token = session.get("access_token")
    else:
        return False

    try:
        request_info = requests.get(
            session.get("token_endpoint"),
            headers={
                "Authorization": "Bearer " + access_token,
                "Accept": "application/json",
            },
        )
    except:
        return False

    if request_info.status_code != 200:
        return False

    if request_info.json().get("me") == None:
        return False

    if request_info.json()["me"].strip("/") != session.get("me").strip("/"):
        return False

    return True
