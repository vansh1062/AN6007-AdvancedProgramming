from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Set
import json
from collections import defaultdict
import threading
import bisect
from enum import Enum
import logging

class MeterReadingException(Exception):
    """Custom exception for meter reading operations"""
    pass

class ReadingStatus(Enum):
    """Enum for reading status"""
    RECEIVED = "received"
    VALIDATED = "validated"
    ARCHIVED = "archived"
    ERROR = "error"

@dataclass
class Address:
    """Class for storing address information"""
    postal_code: str
    unit_number: str
    street_name: str
    building_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "postal_code": self.postal_code,
            "unit_number": self.unit_number,
            "street_name": self.street_name,
            "building_name": self.building_name
        }

@dataclass
class AccountOwner:
    """Class for storing account owner information"""
    owner_id: str
    name: str
    contact_number: str
    email: str
    address: Address
    family_members: Set[str] = None  # Set of family member IDs
    
    def __post_init__(self):
        if self.family_members is None:
            self.family_members = set()
    
    def add_family_member(self, member_id: str):
        self.family_members.add(member_id)
    
    def remove_family_member(self, member_id: str):
        self.family_members.discard(member_id)
    
    def to_dict(self) -> dict:
        return {
            "owner_id": self.owner_id,
            "name": self.name,
            "contact_number": self.contact_number,
            "email": self.email,
            "address": self.address.to_dict(),
            "family_members": list(self.family_members)
        }

@dataclass
class MeterReading:
    """Class for storing individual meter readings"""
    reading_id: str
    meter_id: str
    timestamp: datetime
    value: float
    status: ReadingStatus
    
    def to_dict(self) -> dict:
        return {
            "reading_id": self.reading_id,
            "meter_id": self.meter_id,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "status": self.status.value
        }

class ElectricityAccount:
    """Class representing an electricity account"""
    def __init__(self, account_id: str, meter_id: str, owner: AccountOwner):
        self.account_id = account_id
        self.meter_id = meter_id
        self.owner = owner
        self.readings: List[MeterReading] = []
        self.readings_by_date: Dict[date, List[MeterReading]] = defaultdict(list)
        self.creation_date = datetime.now()
        self.last_reading_date: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def add_reading(self, reading: MeterReading) -> None:
        """Add a new meter reading with thread safety"""
        with self._lock:
            # Insert reading in chronological order
            bisect.insort(self.readings, reading, key=lambda x: x.timestamp)
            reading_date = reading.timestamp.date()
            bisect.insort(
                self.readings_by_date[reading_date],
                reading,
                key=lambda x: x.timestamp
            )
            self.last_reading_date = reading.timestamp
    
    def get_latest_reading(self) -> Optional[MeterReading]:
        """Get the most recent reading"""
        return self.readings[-1] if self.readings else None
    
    def get_readings_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[MeterReading]:
        """Get readings within a date range"""
        result = []
        current_date = start_date
        while current_date <= end_date:
            result.extend(self.readings_by_date[current_date])
            current_date += timedelta(days=1)
        return result
    
    def get_daily_consumption(self, target_date: date) -> float:
        """Calculate total consumption for a specific date"""
        daily_readings = self.readings_by_date[target_date]
        if not daily_readings:
            return 0.0
        return sum(reading.value for reading in daily_readings)
    
    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "meter_id": self.meter_id,
            "owner": self.owner.to_dict(),
            "creation_date": self.creation_date.isoformat(),
            "last_reading_date": self.last_reading_date.isoformat() if self.last_reading_date else None
        }

class MeterDataManager:
    """Central manager for all meter-related data"""
    def __init__(self):
        self.accounts: Dict[str, ElectricityAccount] = {}
        self.meters: Dict[str, str] = {}  # meter_id -> account_id mapping
        self.owners: Dict[str, Set[str]] = defaultdict(set)  # owner_id -> account_ids mapping
        self._lock = threading.Lock()
        self.logger = logging.getLogger('meter_data_manager')
    
    def create_account(
        self,
        meter_id: str,
        owner: AccountOwner
    ) -> ElectricityAccount:
        """Create a new electricity account"""
        with self._lock:
            # Generate account ID (implement your own logic)
            account_id = f"ACC-{len(self.accounts) + 1:06d}"
            
            # Create new account
            account = ElectricityAccount(account_id, meter_id, owner)
            
            # Update mappings
            self.accounts[account_id] = account
            self.meters[meter_id] = account_id
            self.owners[owner.owner_id].add(account_id)
            
            self.logger.info(f"Created new account: {account_id}")
            return account
    
    def add_reading(self, meter_id: str, value: float) -> MeterReading:
        """Add a new meter reading"""
        with self._lock:
            if meter_id not in self.meters:
                raise MeterReadingException(f"Unknown meter ID: {meter_id}")
            
            account_id = self.meters[meter_id]
            account = self.accounts[account_id]
            
            reading = MeterReading(
                reading_id=f"READ-{len(account.readings) + 1:06d}",
                meter_id=meter_id,
                timestamp=datetime.now(),
                value=value,
                status=ReadingStatus.RECEIVED
            )
            
            account.add_reading(reading)
            self.logger.info(f"Added reading for meter {meter_id}: {value} kWh")
            return reading
    
    def get_account_by_meter(self, meter_id: str) -> Optional[ElectricityAccount]:
        """Get account information by meter ID"""
        account_id = self.meters.get(meter_id)
        return self.accounts.get(account_id)
    
    def get_accounts_by_owner(self, owner_id: str) -> List[ElectricityAccount]:
        """Get all accounts belonging to an owner"""
        account_ids = self.owners.get(owner_id, set())
        return [self.accounts[acc_id] for acc_id in account_ids]
    
    def get_consumption_summary(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get consumption summary for a date range"""
        account = self.accounts.get(account_id)
        if not account:
            raise MeterReadingException(f"Unknown account ID: {account_id}")
        
        readings = account.get_readings_by_date_range(start_date, end_date)
        total_consumption = sum(reading.value for reading in readings)
        daily_consumption = defaultdict(float)
        
        for reading in readings:
            daily_consumption[reading.timestamp.date()] += reading.value
        
        return {
            "account_id": account_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_consumption": total_consumption,
            "daily_consumption": {
                date.isoformat(): value 
                for date, value in daily_consumption.items()
            }
        }

    def to_json(self) -> str:
        """Convert all data to JSON for persistence"""
        data = {
            "accounts": {
                acc_id: account.to_dict()
                for acc_id, account in self.accounts.items()
            },
            "meters": self.meters,
            "owners": {
                owner_id: list(account_ids)
                for owner_id, account_ids in self.owners.items()
            }
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'MeterDataManager':
        """Restore data manager from JSON"""
        manager = cls()
        data = json.loads(json_str)
        
        # Reconstruct the data structure
        for acc_id, acc_data in data["accounts"].items():
            # Reconstruct account objects
            pass  # Implement full restoration logic
        
        manager.meters = data["meters"]
        manager.owners = {
            owner_id: set(account_ids)
            for owner_id, account_ids in data["owners"].items()
        }
        
        return manager
