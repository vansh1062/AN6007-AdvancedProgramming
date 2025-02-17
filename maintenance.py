import os
import json
from datetime import datetime

BACKUP_PATH = "storage/readings"

def ensure_backup_directory():
    """Ensure the backup directory exists."""
    os.makedirs(BACKUP_PATH, exist_ok=True)

def save_backup(meter_readings):
    """Save all readings to JSON files"""
    ensure_backup_directory()
    for meter_id, readings in meter_readings.items():
        with open(f"{BACKUP_PATH}/{meter_id}.json", "w") as f:
            json.dump(readings, f, indent=2)
    print("✅ Backup saved successfully!")

def restore_backup():
    """Restore readings from JSON backup files"""
    meter_readings = {}
    ensure_backup_directory()
    
    for filename in os.listdir(BACKUP_PATH):
        meter_id = filename.replace(".json", "")
        with open(f"{BACKUP_PATH}/{filename}", "r") as f:
            meter_readings[meter_id] = json.load(f)

    print(f"✅ Restored data for {len(meter_readings)} meters.")
    return meter_readings

def archive_old_data():
    """Archive old meter readings"""
    archive_path = f"storage/archive/{datetime.now().strftime('%Y-%m-%d')}"
    os.makedirs(archive_path, exist_ok=True)

    for filename in os.listdir(BACKUP_PATH):
        old_path = f"{BACKUP_PATH}/{filename}"
        new_path = f"{archive_path}/{filename}"
        os.rename(old_path, new_path)

    print(f"📦 Data archived to {archive_path}")

# If you want to run maintenance manually
if __name__ == "__main__":
    print("🔄 Running Maintenance Tasks...")
    readings = restore_backup()
    save_backup(readings)
    archive_old_data()
