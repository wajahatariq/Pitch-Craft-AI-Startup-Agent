from tinydb import TinyDB
from datetime import datetime

db = TinyDB("pitchcraft_data.json")

def save_pitch(result):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "name": result["name"],
        "tagline": result["tagline"],
        "pitch": result["pitch"],
        "audience": result["audience"],
        "brand": result["brand"]
    }
    db.insert(entry)
