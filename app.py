from flask import Flask, request, jsonify, render_template_string
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from data_models import storage, Account
from meter_simulator import MeterSimulatorManager
from datetime import datetime, timedelta
import pandas as pd
import threading
import atexit
import signal
import sys
import os

# Initialize Flask and Dash
server = Flask(__name__)
app = Dash(__name__, server=server, url_base_pathname='/dashboard/')
meter_manager = MeterSimulatorManager()

# HTML Templates
REGISTER_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Register Account</title>
    <style>
        body { font-family: Arial; max-width: 500px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input, select { width: 100%; padding: 8px; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; }
    </style>
</head>
<body>
    <h2>Register New Electricity Account</h2>
    <form action="/api/register" method="post">
        <div class="form-group">
            <label>Meter ID (999-999-999):</label>
            <input type="text" name="meter_id" pattern="[0-9]{3}-[0-9]{3}-[0-9]{3}" required>
        </div>
        <div class="form-group">
            <label>Owner Name:</label>
            <input type="text" name="owner_name" required>
        </div>
        <div class="form-group">
            <label>Dwelling Type:</label>
            <select name="dwelling_type" required>
                <option value="HDB">HDB</option>
                <option value="Condo">Condo</option>
                <option value="Landed">Landed</option>
            </select>
        </div>
        <div class="form-group">
            <label>Region:</label>
            <input type="text" name="region" required>
        </div>
        <div class="form-group">
            <label>Area:</label>
            <input type="text" name="area" required>
        </div>
        <button type="submit">Register</button>
    </form>
</body>
</html>
"""

def cleanup():
    """Cleanup function to be called on server shutdown"""
    print("\nPerforming cleanup...")
    
    # Stop all meter simulators
    print("Stopping meter simulators...")
    meter_manager.stop_all()
    
    # Save current state
    print("Saving current state...")
    storage.save_all_data()
    
    # Archive current day's data
    print("Archiving today's data...")
    storage.archive_daily_data()
    
    print("Cleanup completed.")

# Register cleanup functions
atexit.register(cleanup)

# Handle SIGINT (Ctrl+C) and SIGTERM
def signal_handler(signum, frame):
    print(f"\nReceived signal {signum}")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Flask Routes
@server.route('/')
def home():
    return """
    <h1>EMA Electricity Monitoring System</h1>
    <p><a href="/register">Register New Account</a></p>
    <p><a href="/dashboard">View Dashboard</a></p>
    """

@server.route('/register', methods=['GET'])
def register_form():
    return render_template_string(REGISTER_FORM)

@server.route('/api/register', methods=['POST'])
def register_account():
    try:
        account = Account(
            meter_id=request.form['meter_id'],
            owner_name=request.form['owner_name'],
            dwelling_type=request.form['dwelling_type'],
            region=request.form['region'],
            area=request.form['area']
        )
        storage.save_account(account)
        
        # Start automatic meter reading simulation
        meter_manager.add_meter(account.meter_id)
        
        return jsonify({"status": "success", "message": "Account registered successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# Dash Layout
app.layout = html.Div(style={'backgroundColor': '#f5f5f5', 'fontFamily': 'Arial', 'padding': '20px'}, children=[
    html.H1("EMA Electricity Management Dashboard", 
            style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # Meter Selection
    html.Div([
        html.Label('Select Meter ID:'),
        dcc.Dropdown(
            id='meter-selector',
            options=[],
            placeholder='Select a meter to view'
        )
    ], style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'marginBottom': '20px'}),
    
    # Current Reading
    html.Div([
        html.H2("Current Reading"),
        html.Div(id='current-reading-display', style={'fontSize': '24px', 'fontWeight': 'bold'})
    ], style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'marginBottom': '20px'}),
    
    # Today's Consumption
    html.Div([
        html.H2("Today's Consumption"),
        dcc.Graph(id='today-consumption'),
        dcc.Interval(id='consumption-update', interval=30000)
    ], style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'marginBottom': '20px'}),
    
    # Weekly Consumption
    html.Div([
        html.H2("Weekly Consumption"),
        dcc.Graph(id='weekly-consumption')
    ], style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'marginBottom': '20px'})
])

# Dash Callbacks
@app.callback(
    Output('meter-selector', 'options'),
    Input('consumption-update', 'n_intervals')
)
def update_meter_options(_):
    return [{'label': f'Meter {meter_id}', 'value': meter_id} 
            for meter_id in storage.accounts.keys()]

@app.callback(
    [Output('current-reading-display', 'children'),
     Output('today-consumption', 'figure'),
     Output('weekly-consumption', 'figure')],
    [Input('meter-selector', 'value'),
     Input('consumption-update', 'n_intervals')]
)
def update_visualizations(meter_id, _):
    if not meter_id:
        return "No meter selected", go.Figure(), go.Figure()
    
    account = storage.accounts.get(meter_id)
    if not account:
        return "Invalid meter ID", go.Figure(), go.Figure()
    
    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Current Reading Display
    current_reading = "No readings yet"
    if today in account.readings and account.readings[today]:
        latest_reading = account.readings[today][-1]
        current_reading = f"Current Reading: {latest_reading.value:.1f} kWh"
    
    # Today's Consumption Graph
    today_fig = go.Figure()
    if today in account.readings:
        readings = account.readings[today]
        times = [r.timestamp.strftime("%H:%M") for r in readings]
        values = [r.value for r in readings]
        today_fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode='lines+markers',
            name='Consumption'
        ))
        today_fig.update_layout(
            title='Today\'s Consumption Pattern',
            xaxis_title='Time',
            yaxis_title='Consumption (kWh)'
        )
    
    # Weekly Consumption Graph
    week_fig = go.Figure()
    week_data = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        if date in account.readings:
            readings = account.readings[date]
            if readings:
                daily_consumption = readings[-1].value - readings[0].value
                week_data.append({
                    'date': date,
                    'consumption': daily_consumption
                })
    
    if week_data:
        df = pd.DataFrame(week_data)
        week_fig = px.bar(
            df,
            x='date',
            y='consumption',
            title='Weekly Consumption'
        )
        week_fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Daily Consumption (kWh)'
        )
    
    return current_reading, today_fig, week_fig

if __name__ == '__main__':
    try:
        # Create storage directories
        os.makedirs('storage/accounts', exist_ok=True)
        os.makedirs('storage/readings', exist_ok=True)
        os.makedirs('storage/logs', exist_ok=True)
        os.makedirs('storage/archive', exist_ok=True)
        
        # Restore previous state if exists
        storage.restore_from_logs()
        
        # Start meter simulators for existing accounts
        for meter_id in storage.accounts:
            meter_manager.add_meter(meter_id)
        
        # Start the server
        server.run(host='127.0.0.1', port=8080, debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        cleanup()
        sys.exit(1)
    finally:
        cleanup()
    
    
    
    
    
    