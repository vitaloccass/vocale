from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    scopes=SCOPES
)

creds = flow.run_local_server(port=0)

# Afficher les valeurs à copier
result = {
    "refresh_token": creds.refresh_token,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret
}

print("\n✅ Copiez ceci dans Render GOOGLE_CREDENTIALS:")
print(json.dumps(result))