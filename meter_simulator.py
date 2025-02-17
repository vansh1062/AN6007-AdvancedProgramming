import threading
import time
from datetime import datetime
import requests
import random

class MeterSimulator:
    def __init__(self, meter_id, base_consumption=100.0):
        self.meter_id = meter_id
        self.current_reading = base_consumption
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the meter simulation"""
        self.running = True
        self.thread = threading.Thread(target=self._run_simulation)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the meter simulation"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _run_simulation(self):
        """Run the meter reading simulation"""
        while self.running:
            current_hour = datetime.now().hour
            
            # Only send readings between 01:00 and 23:59
            if current_hour != 0:
                # Simulate some random consumption
                self.current_reading += random.uniform(0.5, 2.0)
                
                try:
                    # Send reading to API
                    response = requests.post('http://localhost:8080/api/reading', 
                                          data={
                                              'meter_id': self.meter_id,
                                              'reading': round(self.current_reading, 1)
                                          })
                    print(f"Sent reading for {self.meter_id}: {self.current_reading:.1f} kWh")
                except Exception as e:
                    print(f"Error sending reading: {e}")
            
            # Wait for 30 minutes (in this case, we'll use 30 seconds for demonstration)
            time.sleep(30)  # Reduced for testing, should be 1800 in production

class MeterSimulatorManager:
    def __init__(self):
        self.simulators = {}
    
    def add_meter(self, meter_id, base_consumption=100.0):
        """Add a new meter to simulate"""
        simulator = MeterSimulator(meter_id, base_consumption)
        self.simulators[meter_id] = simulator
        simulator.start()
    
    def stop_all(self):
        """Stop all meter simulations"""
        for simulator in self.simulators.values():
            simulator.stop()

# Usage example
if __name__ == "__main__":
    manager = MeterSimulatorManager()
    
    # Add some test meters
    test_meters = [
        ("123-456-789", 100.0),
        ("234-567-890", 150.0),
        ("345-678-901", 200.0)
    ]
    
    print("Starting meter simulations...")
    for meter_id, base_consumption in test_meters:
        manager.add_meter(meter_id, base_consumption)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulations...")
        manager.stop_all()