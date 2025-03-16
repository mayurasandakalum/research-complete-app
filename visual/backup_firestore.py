import json
from datetime import datetime
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase():
    """Initialize Firebase if not already initialized"""
    try:
        # Get the current directory
        current_dir = Path(__file__).parent
        cred_path = current_dir / "serviceAccountKey.json"

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)

        return firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None


def backup_collection(db, collection_name):
    """Backup a single collection"""
    try:
        docs = db.collection(collection_name).get()
        collection_data = []

        for doc in docs:
            doc_data = doc.to_dict()
            # Convert datetime objects to ISO format strings
            for key, value in doc_data.items():
                if isinstance(value, datetime):
                    doc_data[key] = value.isoformat()

            collection_data.append({"id": doc.id, "data": doc_data})

        return collection_data
    except Exception as e:
        print(f"Error backing up collection {collection_name}: {e}")
        return []


def backup_firestore():
    """Backup all collections from Firestore"""
    db = initialize_firebase()
    if not db:
        return

    try:
        # Get all collections
        collections = db.collections()
        backup_data = {}

        for collection in collections:
            print(f"Backing up collection: {collection.id}")
            backup_data[collection.id] = backup_collection(db, collection.id)

        # Create backup directory if it doesn't exist
        backup_dir = Path(__file__).parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create backup file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"firestore_backup_{timestamp}.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        print(f"Backup completed successfully! File saved as: {backup_file}")

    except Exception as e:
        print(f"Error during backup: {e}")


if __name__ == "__main__":
    backup_firestore()
