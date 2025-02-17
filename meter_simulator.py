import threading
import time
import requests
import random
from datetime import datetime

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
        """Simulate electricity meter readings"""
        while self.running:
            current_hour = datetime.now().hour

            # Only send readings between 01:00 and 23:59
            if current_hour != 0:
                self.current_reading += random.uniform(0.5, 2.0)

                try:
                    response = requests.post(
                        'http://127.0.0.1:8080/api/meter/reading',
                        json={
                            'meter_id': self.meter_id,
                            'reading': round(self.current_reading, 1),
                            'timestamp': datetime.now().isoformat()
                        },
                        timeout=5  # Set timeout to prevent hanging requests
                    )

                    if response.status_code == 200:
                        print(f"✅ Sent reading for {self.meter_id}: {self.current_reading:.1f} kWh")
                    else:
                        print(f"⚠️ Failed to send reading for {self.meter_id}: {response.text}")

                except requests.exceptions.ConnectionError:
                    print(f"❌ API is not running! Ensure `app.py` is started.")
                    time.sleep(10)  # Wait before retrying
                except Exception as e:
                    print(f"❌ Error sending reading: {e}")

            time.sleep(30)  # Use 1800 for production

class MeterSimulatorManager:
    def __init__(self):
        self.simulators = {}

    def add_meter(self, meter_id, base_consumption=100.0):
        """Add a new simulated meter"""
        if meter_id not in self.simulators:
            simulator = MeterSimulator(meter_id, base_consumption)
            self.simulators[meter_id] = simulator
            simulator.start()

    def stop_all(self):
        """Stop all meter simulations"""
        for simulator in self.simulators.values():
            simulator.stop()

if __name__ == "__main__":
    manager = MeterSimulatorManager()

    test_meters = [
        ("123-456-789", 100.0),
        ("234-567-890", 150.0),
        ("345-678-901", 200.0)
    ]

    print("Starting Meter Simulations...")
    for meter_id, base_consumption in test_meters:
        manager.add_meter(meter_id, base_consumption)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Meter Simulations...")
        manager.stop_all()
