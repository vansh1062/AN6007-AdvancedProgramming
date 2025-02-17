from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import maintenance  # Import backup and restore

app = Flask(__name__)

# Restore data from maintenance.py
meter_readings = maintenance.restore_backup()

@app.route('/')
def home():
    return jsonify({"message": "Electricity Meter API is Running!"})

@app.route('/api/meter/reading', methods=['POST'])
def receive_reading():
    """Receive meter readings from the simulator"""
    try:
        data = request.json
        meter_id = data.get('meter_id')
        reading = data.get('reading')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if not meter_id or reading is None:
            return jsonify({"error": "Missing meter_id or reading"}), 400

        if meter_id not in meter_readings:
            meter_readings[meter_id] = []

        meter_readings[meter_id].append({
            "reading": float(reading),
            "timestamp": timestamp
        })

        # Save backup after every new reading
        maintenance.save_backup(meter_readings)

        return jsonify({"success": True, "message": "Reading stored successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/meter/reading/<meter_id>', methods=['GET'])
def get_meter_readings(meter_id):
    """Fetch stored meter readings"""
    if meter_id in meter_readings:
        return jsonify(meter_readings[meter_id]), 200
    return jsonify({"error": "No readings found"}), 404

@app.route('/api/meter/reading/all', methods=['GET'])
def get_all_meter_ids():
    """Return all meter IDs that have readings"""
    if not meter_readings:
        return jsonify([])  # Return empty list if no meters found
    return jsonify(list(meter_readings.keys()))

if __name__ == '__main__':
    print("✅ Starting API on http://127.0.0.1:8080")
    app.run(host='127.0.0.1', port=8080, debug=True)
