from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from data_models import storage
import requests

# Initialize Dash app
app = Dash(__name__)

# Define the layout with inline styles instead of html.Style
app.layout = html.Div([
    html.H1("EMA Electricity Management Dashboard", 
            style={'textAlign': 'center', 'marginBottom': '30px', 'fontFamily': 'Arial'}),
    
    # System Status Card
    html.Div([
        html.H2("System Status"),
        html.Div(id='system-status'),
        dcc.Interval(id='status-update', interval=60000)  # Update every minute
    ], style={
        'padding': '20px',
        'margin': '20px',
        'borderRadius': '10px',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'backgroundColor': 'white'
    }),
    
    # Real-time Monitoring
    html.Div([
        html.H2("Real-time Consumption Monitoring"),
        dcc.Graph(id='live-consumption'),
        dcc.Interval(id='consumption-update', interval=30000)  # Update every 30 seconds
    ], style={
        'padding': '20px',
        'margin': '20px',
        'borderRadius': '10px',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'backgroundColor': 'white'
    }),
    
    # Regional Analysis
    html.Div([
        html.H2("Regional Consumption Analysis"),
        dcc.DatePickerRange(
            id='date-range',
            start_date=(datetime.now() - timedelta(days=30)).date(),
            end_date=datetime.now().date()
        ),
        dcc.Graph(id='regional-analysis')
    ], style={
        'padding': '20px',
        'margin': '20px',
        'borderRadius': '10px',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'backgroundColor': 'white'
    }),
    
    # Maintenance Controls
    html.Div([
        html.H2("System Maintenance"),
        html.Button(
            'Start Maintenance',
            id='maintenance-button',
            style={
                'backgroundColor': '#4CAF50',
                'color': 'white',
                'padding': '10px 20px',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer'
            }
        ),
        html.Div(id='maintenance-status')
    ], style={
        'padding': '20px',
        'margin': '20px',
        'borderRadius': '10px',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'backgroundColor': 'white'
    })
], style={'backgroundColor': '#f5f5f5', 'fontFamily': 'Arial'})

# Callbacks
@app.callback(
    Output('system-status', 'children'),
    Input('status-update', 'n_intervals')
)
def update_system_status(_):
    total_accounts = len(storage.accounts)
    current_time = datetime.now()
    today = current_time.strftime("%Y-%m-%d")
    
    # Count active meters today
    active_meters = sum(
        1 for acc in storage.accounts.values()
        if today in acc.readings
    )
    
    # Calculate total consumption today
    total_consumption = sum(
        sum(reading.value for reading in acc.readings.get(today, []))
        for acc in storage.accounts.values()
    )
    
    return html.Div([
        html.P(f"Total Accounts: {total_accounts}"),
        html.P(f"Active Meters Today: {active_meters}"),
        html.P(f"Total Consumption Today: {total_consumption:.2f} kWh"),
        html.P(f"Last Updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    ])

@app.callback(
    Output('live-consumption', 'figure'),
    Input('consumption-update', 'n_intervals')
)
def update_live_consumption(_):
    # Get last hour's data
    current_time = datetime.now()
    hour_ago = current_time - timedelta(hours=1)
    
    data = []
    for account in storage.accounts.values():
        for date, readings in account.readings.items():
            for reading in readings:
                if hour_ago <= reading.timestamp <= current_time:
                    data.append({
                        'timestamp': reading.timestamp,
                        'consumption': reading.value,
                        'region': account.region
                    })
    
    df = pd.DataFrame(data)
    if not df.empty:
        fig = px.line(df, 
                     x='timestamp', 
                     y='consumption',
                     color='region',
                     title='Last Hour Consumption by Region')
        return fig
    return go.Figure()

@app.callback(
    Output('regional-analysis', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date')
)
def update_regional_analysis(start_date, end_date):
    data = []
    for account in storage.accounts.values():
        region_consumption = 0
        for date, readings in account.readings.items():
            if start_date <= date <= end_date and readings:
                # Calculate daily consumption
                daily_consumption = readings[-1].value - readings[0].value
                region_consumption += daily_consumption
                
        data.append({
            'region': account.region,
            'consumption': region_consumption,
            'dwelling_type': account.dwelling_type
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        fig = px.bar(df,
                    x='region',
                    y='consumption',
                    color='dwelling_type',
                    title='Regional Consumption Analysis',
                    barmode='group')
        return fig
    return go.Figure()

@app.callback(
    Output('maintenance-status', 'children'),
    Input('maintenance-button', 'n_clicks'),
    State('maintenance-button', 'n_clicks')
)
def trigger_maintenance(n_clicks, prev_clicks):
    if n_clicks and n_clicks != prev_clicks:
        try:
            # Call maintenance API
            response = requests.post('http://localhost:8080/api/maintenance/start')
            if response.status_code == 200:
                return html.Div("Maintenance completed successfully",
                              style={'color': 'green'})
            else:
                return html.Div(f"Error: {response.json().get('message')}",
                              style={'color': 'red'})
        except Exception as e:
            return html.Div(f"Error: {str(e)}", style={'color': 'red'})
    return html.Div("Click button to start maintenance")

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)