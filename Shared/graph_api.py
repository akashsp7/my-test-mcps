if client.get_access_token():
    url = f"{client.base_url}/users/{YOUR_EMAIL}"
    headers = {'Authorization': f'Bearer {client.access_token}'}
    response = requests.get(url, headers=headers)

    print(f"Status: {response.status_code}")
    print(f"Error: {response.text}")

    # Check token details
    import base64
    token_parts = client.access_token.split('.')
    payload = base64.b64decode(token_parts[1] + '==').decode('utf-8')
    print(f"Token payload: {payload}")