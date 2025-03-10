import firebase_admin
from firebase_admin import credentials, firestore

# Path to your service account key JSON file
service_account_path = "./learn-pal-firebase-adminsdk-ugedp-fcb865a7d8.json"

# Initialize Firebase
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

# Access Firestore
db = firestore.client()
