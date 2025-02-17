from datetime import datetime, timedelta
import pandas as pd
import os
from data_models import storage

class MaintenanceJobs:
    def __init__(self):
        self.archive_path = "storage/archive"
        os.makedirs(self.archive_path, exist_ok=True)
    
    def run_daily_maintenance(self):
        """Run all daily maintenance tasks"""
        try:
            print("Starting daily maintenance...")
            
            # Archive current day's data
            self._archive_daily_data()
            
            # Clean up old data
            self._cleanup_old_data()
            
            # Prepare denormalized data
            self._prepare_daily_denormalized()
            
            # Prepare for new day
            self._prepare_new_day()
            
            print("Daily maintenance completed successfully")
            return True
        except Exception as e:
            print(f"Error in daily maintenance: {e}")
            return False
    
    def run_monthly_maintenance(self):
        """Run monthly maintenance tasks"""
        try:
            print("Starting monthly maintenance...")
            
            # Archive monthly data
            self._archive_monthly_data()
            
            # Prepare monthly denormalized data
            self._prepare_monthly_denormalized()
            
            print("Monthly maintenance completed successfully")
            return True
        except Exception as e:
            print(f"Error in monthly maintenance: {e}")
            return False
    
    def _archive_daily_data(self):
        """Archive previous day's readings"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        daily_archive_path = f"{self.archive_path}/daily/{yesterday}"
        os.makedirs(daily_archive_path, exist_ok=True)
        
        for account in storage.accounts.values():
            if yesterday in account.readings:
                # Save readings to archive
                readings_data = [
                    {
                        "timestamp": r.timestamp.isoformat(),
                        "value": r.value
                    }
                    for r in account.readings[yesterday]
                ]
                
                with open(f"{daily_archive_path}/{account.meter_id}.json", 'w') as f:
                    pd.DataFrame(readings_data).to_json(f, orient='records')
                
                # Remove from memory
                del account.readings[yesterday]
    
    def _cleanup_old_data(self):
        """Clean up data older than 30 days"""
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        for account in storage.accounts.values():
            # Remove old readings
            account.readings = {
                date: readings
                for date, readings in account.readings.items()
                if date >= cutoff_date
            }
    
    def _prepare_daily_denormalized(self):
        """Prepare denormalized data for the day"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Collect consumption data
        data = []
        for account in storage.accounts.values():
            if yesterday in account.readings:
                readings = account.readings[yesterday]
                if readings:
                    daily_consumption = readings[-1].value - readings[0].value
                    data.append({
                        'Date': yesterday,
                        'Region': account.region,
                        'Area': account.area,
                        'Dwelling_Type': account.dwelling_type,
                        'Consumption_kWh': daily_consumption,
                        'Meter_ID': account.meter_id
                    })
        
        if data:
            df = pd.DataFrame(data)
            denorm_path = f"{self.archive_path}/denormalized"
            os.makedirs(denorm_path, exist_ok=True)
            df.to_csv(f"{denorm_path}/daily_{yesterday}.csv", index=False)
    
    def _prepare_new_day(self):
        """Prepare system for new day"""
        # Clear temporary data
        temp_path = "storage/temp"
        if os.path.exists(temp_path):
            for filename in os.listdir(temp_path):
                os.remove(os.path.join(temp_path, filename))
    
    def _archive_monthly_data(self):
        """Archive previous month's data"""
        last_month = (datetime.now().replace(day=1) - timedelta(days=1))
        month_str = last_month.strftime('%Y-%m')
        
        monthly_archive_path = f"{self.archive_path}/monthly/{month_str}"
        os.makedirs(monthly_archive_path, exist_ok=True)
        
        # Move daily files to monthly archive
        denorm_path = f"{self.archive_path}/denormalized"
        if os.path.exists(denorm_path):
            for filename in os.listdir(denorm_path):
                if filename.startswith('daily_') and month_str in filename:
                    os.rename(
                        f"{denorm_path}/{filename}",
                        f"{monthly_archive_path}/{filename}"
                    )
    
    def _prepare_monthly_denormalized(self):
        """Prepare denormalized monthly data"""
        last_month = (datetime.now().replace(day=1) - timedelta(days=1))
        month_str = last_month.strftime('%Y-%m')
        
        # Read all daily files
        monthly_data = []
        monthly_archive_path = f"{self.archive_path}/monthly/{month_str}"
        
        if os.path.exists(monthly_archive_path):
            for filename in os.listdir(monthly_archive_path):
                if filename.startswith('daily_'):
                    df = pd.read_csv(f"{monthly_archive_path}/{filename}")
                    monthly_data.append(df)
        
        if monthly_data:
            # Combine all daily data
            monthly_df = pd.concat(monthly_data)
            
            # Create aggregated views
            aggregations = {
                'by_region': monthly_df.groupby('Region')['Consumption_kWh'].sum(),
                'by_dwelling': monthly_df.groupby(['Region', 'Dwelling_Type'])['Consumption_kWh'].sum(),
                'by_area': monthly_df.groupby(['Region', 'Area'])['Consumption_kWh'].sum()
            }
            
            # Save aggregated data
            for name, data in aggregations.items():
                data.to_csv(f"{monthly_archive_path}/{name}_{month_str}.csv")

# Create global maintenance jobs instance
maintenance_jobs = MaintenanceJobs()