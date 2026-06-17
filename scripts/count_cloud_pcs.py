import os
from dotenv import load_dotenv

load_dotenv()
os.environ["AUTH_MODE"] = "client_secret"

import httpx
from graphmind.auth.token import get_token

headers = {"Authorization": f"Bearer {get_token()}"}
url = "https://graph.microsoft.com/v1.0/deviceManagement/virtualEndpoint/cloudPCs?$top=999"
items = []

with httpx.Client(timeout=60) as client:
    while url:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

print(f"Total Cloud PCs: {len(items)}")
for pc in items:
    name = pc.get("displayName", "?")
    user = pc.get("userPrincipalName", "?")
    status = pc.get("status", "?")
    print(f"  - {name} | {user} | status={status}")
