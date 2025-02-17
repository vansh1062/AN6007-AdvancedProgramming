from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
import pickle

@dataclass
class MeterReading:
    timestamp: datetime
    value: float

@dataclass
class Account:
    meter_id: str
    owner_name: str
    dwelling_type: str
    region: str
    area: str
    readings: Dict[str, List[MeterReading]] = field(default_factory=dict)

class Storage:
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.base_path = "storage"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories"""
        paths = [
            "storage/accounts",
            "storage/readings",
            "storage/logs",
            "storage/archive"
        ]
        for path in paths:
            os.makedirs(path, exist_ok=True)
    
    def save_account(self, account: Account):
        """Save account and log the operation"""
        self.accounts[account.meter_id] = account
        
        # Save to file
        with open(f"storage/accounts/{account.meter_id}.pkl", 'wb') as f:
            pickle.dump(account, f)
        
        # Log operation
        self._log_operation("create_account", {
            "meter_id": account.meter_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_reading(self, meter_id: str, reading: float):
        """Add meter reading and log the operation"""
        if meter_id not in self.accounts:
            raise ValueError("Account not found")
        
        current_time = datetime.now()
        date_key = current_time.strftime("%Y-%m-%d")
        
        if date_key not in self.accounts[meter_id].readings:
            self.accounts[meter_id].readings[date_key] = []
        
        reading_obj = MeterReading(current_time, reading)
        self.accounts[meter_id].readings[date_key].append(reading_obj)
        
        # Save updated account
        with open(f"storage/accounts/{meter_id}.pkl", 'wb') as f:
            pickle.dump(self.accounts[meter_id], f)
        
        # Log operation
        self._log_operation("add_reading", {
            "meter_id": meter_id,
            "reading": reading,
            "timestamp": current_time.isoformat()
        })
    
    def _log_operation(self, operation_type: str, data: dict):
        """Log operations for recovery"""
        log_entry = {
            "operation": operation_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        log_file = f"storage/logs/operations_{datetime.now().strftime('%Y%m')}.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def restore_from_logs(self):
        """Restore system state from logs"""
        self.accounts.clear()
        
        # First restore accounts
        accounts_path = "storage/accounts"
        for filename in os.listdir(accounts_path):
            if filename.endswith('.pkl'):
                with open(f"{accounts_path}/{filename}", 'rb') as f:
                    account = pickle.load(f)
                    self.accounts[account.meter_id] = account
    
    def archive_daily_data(self):
        """Archive current day's data"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        archive_path = f"storage/archive/daily/{current_date}"
        os.makedirs(archive_path, exist_ok=True)
        
        for account in self.accounts.values():
            if current_date in account.readings:
                readings = account.readings[current_date]
                with open(f"{archive_path}/{account.meter_id}.json", 'w') as f:
                    json.dump([{
                        "timestamp": r.timestamp.isoformat(),
                        "value": r.value
                    } for r in readings], f)
                
                # Clear from memory
                del account.readings[current_date]
                
    def save_all_data(self):
        """Save all current data to storage"""
        try:
            # Save accounts
            for meter_id, account in self.accounts.items():
                account_file = f"{self.base_path}/accounts/{meter_id}.pkl"
                with open(account_file, 'wb') as f:
                    pickle.dump(account, f)
            
            # Log the save operation
            self._log_operation("save_all", {
                "timestamp": datetime.now().isoformat(),
                "accounts_saved": list(self.accounts.keys())
            })
            
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def archive_daily_data(self):
        """Archive current day's data"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            archive_path = f"{self.base_path}/archive/daily/{current_date}"
            os.makedirs(archive_path, exist_ok=True)
            
            for meter_id, account in self.accounts.items():
                if current_date in account.readings:
                    # Save readings to archive
                    archive_file = f"{archive_path}/{meter_id}.json"
                    readings_data = [
                        {
                            "timestamp": reading.timestamp.isoformat(),
                            "value": reading.value
                        }
                        for reading in account.readings[current_date]
                    ]
                    
                    with open(archive_file, 'w') as f:
                        json.dump(readings_data, f, indent=2)
        
        # Log the archive operation
            self._log_operation("archive_daily", {
                "date": current_date,
                "accounts_archived": list(self.accounts.keys())
            })
        
            return True
        except Exception as e:
            print(f"Error archiving data: {e}")
            return False

# Global storage instance
storage = Storage()