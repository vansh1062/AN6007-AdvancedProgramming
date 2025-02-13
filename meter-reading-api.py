from flask import Flask, request, jsonify
from datetime import datetime
import re
import json
import logging
from typing import Dict, List
import threading
import time

# Configure logging
logging.basicConfig(
    filename='meter_readings.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MeterReading:
    def __init__(self, meter_id: str, reading: float, timestamp: datetime):
        self.meter_id = meter_id
        self.reading = reading
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        return {
            'meter_id': self.meter_id,
            'reading': self.reading,
            'timestamp': self.timestamp.isoformat()
        }

class MeterReadingSystem:
    def __init__(self):
        self.readings: Dict[str, List[MeterReading]] = {}
        self.lock = threading.Lock()

    def validate_meter_id(self, meter_id: str) -> bool:
        """Validate meter ID format (999-999-999)"""
        pattern = r'^\d{3}-\d{3}-\d{3}$'
        return bool(re.match(pattern, meter_id))

    def validate_reading(self, reading: float) -> bool:
        """Validate reading format (99999.9)"""
        return 0 <= reading <= 99999.9

    def add_reading(self, meter_id: str, reading: float) -> bool:
        if not self.validate_meter_id(meter_id):
            return False, "Invalid meter ID format. Must be 999-999-999"
        
        if not self.validate_reading(reading):
            return False, "Invalid reading. Must be between 0 and 99999.9"

        with self.lock:
            new_reading = MeterReading(meter_id, reading, datetime.now())
            if meter_id not in self.readings:
                self.readings[meter_id] = []
            self.readings[meter_id].append(new_reading)
            
            # Log the reading
            logging.info(f"New reading added: {new_reading.to_dict()}")
            
            return True, "Reading added successfully"

    def get_latest_reading(self, meter_id: str) -> Dict:
        if meter_id not in self.readings:
            return None
        return self.readings[meter_id][-1].to_dict()

    def get_readings_by_date(self, meter_id: str, date: datetime) -> List[Dict]:
        if meter_id not in self.readings:
            return []
        return [
            reading.to_dict() 
            for reading in self.readings[meter_id] 
            if reading.timestamp.date() == date.date()
        ]

app = Flask(__name__)
meter_system = MeterReadingSystem()
logger = setup_logging_for_meter_api(app)

@app.route('/api/meter/reading', methods=['POST'])
def submit_reading():
    try:
        data = request.get_json()
        
        if not data or 'meter_id' not in data or 'reading' not in data:
            logger.log_error({
                'type': 'ValidationError',
                'message': 'Missing required fields',
                'details': {'received_data': data}
            })
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

    success, message = meter_system.add_reading(
        data['meter_id'],
        float(data['reading'])
    )

    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@app.route('/api/meter/reading/<meter_id>', methods=['GET'])
def get_reading(meter_id):
    reading = meter_system.get_latest_reading(meter_id)
    if reading:
        return jsonify({
            'success': True,
            'data': reading
        })
    return jsonify({
        'success': False,
        'error': 'No readings found for this meter'
    }), 404

@app.route('/api/meter/simulate', methods=['GET'])
def simulate_reading():
    """Endpoint to simulate a meter reading input form"""
    return '''
        <html>
            <body>
                <h2>Simulate Meter Reading</h2>
                <form id="readingForm">
                    <div>
                        <label>Meter ID (format: 999-999-999):</label><br>
                        <input type="text" id="meterId" required pattern="\d{3}-\d{3}-\d{3}">
                    </div>
                    <div>
                        <label>Reading (0-99999.9 kWh):</label><br>
                        <input type="number" id="reading" step="0.1" min="0" max="99999.9" required>
                    </div>
                    <button type="submit">Submit Reading</button>
                </form>
                <div id="result"></div>

                <script>
                    document.getElementById('readingForm').onsubmit = async (e) => {
                        e.preventDefault();
                        const meterId = document.getElementById('meterId').value;
                        const reading = document.getElementById('reading').value;
                        
                        try {
                            const response = await fetch('/api/meter/reading', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    meter_id: meterId,
                                    reading: parseFloat(reading)
                                })
                            });
                            const result = await response.json();
                            document.getElementById('result').innerHTML = 
                                `<p>${result.success ? 'Success' : 'Error'}: ${result.message || result.error}</p>`;
                        } catch (error) {
                            document.getElementById('result').innerHTML = 
                                `<p>Error: ${error.message}</p>`;
                        }
                    };
                </script>
            </body>
        </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)
