import requests
import json
from datetime import datetime

# Configuration (set these with your actual values)
CLIENT_ID = "your_client_id"
TENANT_ID = "your_tenant_id"
CLIENT_SECRET = "your_secret_value"

class GraphEmailClient:
    def __init__(self, client_id, tenant_id, client_secret):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://graph.microsoft.com/v1.0"

    def get_access_token(self):
        """Get access token using client credentials flow"""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }

        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            print("✅ Access token obtained")
            return True
        else:
            print(f"❌ Token error: {response.text}")
            return False

    def get_mail_folders(self, user_email=None):
        """List all mail folders"""
        if not self.access_token:
            return None

        # Use specific user or 'me' for authenticated user
        endpoint = f"users/{user_email}/mailFolders" if user_email else "me/mailFolders"
        url = f"{self.base_url}/{endpoint}"

        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()['value']
        else:
            print(f"❌ Folders error: {response.text}")
            return None

    def get_emails_from_folder(self, folder_name="Inbox", user_email=None, top=10):
        """Fetch emails from specific folder"""
        if not self.access_token:
            return None

        # First get folder ID
        folders = self.get_mail_folders(user_email)
        if not folders:
            return None

        folder_id = None
        for folder in folders:
            if folder['displayName'].lower() == folder_name.lower():
                folder_id = folder['id']
                break

        if not folder_id:
            print(f"❌ Folder '{folder_name}' not found")
            return None

        # Get emails from folder
        endpoint = f"users/{user_email}/mailFolders/{folder_id}/messages" if user_email else f"me/mailFolders/{folder_id}/messages"
        url = f"{self.base_url}/{endpoint}?$top={top}&$select=subject,from,receivedDateTime,bodyPreview,internetMessageId"

        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()['value']
        else:
            print(f"❌ Emails error: {response.text}")
            return None

# Initialize client
client = GraphEmailClient(CLIENT_ID, TENANT_ID, CLIENT_SECRET)

# Test authentication
if client.get_access_token():
    print("🔗 Connected to Graph API")

    # List folders
    print("\n📁 Available folders:")
    folders = client.get_mail_folders()
    if folders:
        for folder in folders[:10]:  # Show first 10
            print(f"  • {folder['displayName']} ({folder['totalItemCount']} items)")

    # Test fetch emails from Inbox
    print(f"\n📧 Recent emails from Inbox:")
    emails = client.get_emails_from_folder("Inbox", top=5)
    if emails:
        for email in emails:
            print(f"  • {email['subject']}")
            print(f"    From: {email['from']['emailAddress']['address']}")
            print(f"    Date: {email['receivedDateTime']}")
            print()