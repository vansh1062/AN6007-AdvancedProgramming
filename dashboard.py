from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import requests
import pandas as pd
import plotly.express as px

# Initialize Dash
app = Dash(__name__)
app.title = "Electricity Usage Dashboard"

# Define the Dashboard Layout
app.layout = html.Div([
    html.H1("Electricity Usage Dashboard", style={'textAlign': 'center'}),

    # Dropdown for Meter Selection
    html.Div([
        html.Label("Select Meter ID:"),
        dcc.Dropdown(id='meter-selector', options=[], placeholder='Select a meter')
    ], style={'marginBottom': '20px'}),

    # Display Current Reading
    html.Div([
        html.H3("Live Meter Readings"),
        dash_table.DataTable(
            id='live-meter-table',
            columns=[
                {"name": "Timestamp", "id": "timestamp"},
                {"name": "Reading (kWh)", "id": "reading"}
            ],
            data=[],
            style_table={'overflowX': 'auto'}
        )
    ]),

    # Electricity Consumption Graph
    dcc.Graph(id='consumption-graph'),

    # Interval Component for Periodic API Updates
    dcc.Interval(
        id='interval-component',
        interval=5000,  # Refresh every 5 seconds
        n_intervals=0
    )
])

# Fetch Available Meters
@app.callback(
    Output('meter-selector', 'options'),
    Input('interval-component', 'n_intervals')
)
def update_meter_options(_):
    """Fetch available meter IDs from the API."""
    try:
        response = requests.get("http://127.0.0.1:8080/api/meter/reading/all")
        if response.status_code == 200:
            meters = response.json()
            if not isinstance(meters, list) or not meters:
                return []  # Handle empty response
            return [{'label': meter, 'value': meter} for meter in meters]
    except Exception as e:
        print(f"⚠️ Error fetching meter IDs: {e}")
    return []

# Update Live Data & Graph
@app.callback(
    [Output('live-meter-table', 'data'),
     Output('consumption-graph', 'figure')],
    [Input('meter-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_dashboard(meter_id, _):
    """Fetch the latest meter readings and update the table & graph."""
    if not meter_id:
        return [], px.line(title="No Data Available")

    try:
        response = requests.get(f"http://127.0.0.1:8080/api/meter/reading/{meter_id}")
        if response.status_code == 200:
            meter_data = response.json()
        else:
            return [], px.line(title="No Readings Found")
    except Exception as e:
        print(f"⚠️ Error fetching readings: {e}")
        return [], px.line(title="API Error")

    df = pd.DataFrame(meter_data)

    return df.to_dict('records'), px.line(df, x='timestamp', y='reading', title=f"Consumption for Meter {meter_id}")

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
