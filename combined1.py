# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 13:56:41 2025

@author: HP
"""

import os
import csv
import logging
import json
import threading
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify, render_template, g
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
from dash import Dash, dash_table, callback, Output, Input
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import bisect
from enum import Enum

app = Flask(__name__)

# ========== Logging System ==========
class MeterLoggingSystem:
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = log_directory
        self.setup_log_directory()
        self.setup_loggers()
        self.lock = threading.Lock()

    def setup_log_directory(self):
        os.makedirs(self.log_directory, exist_ok=True)

    def setup_loggers(self):
        self.request_logger = logging.getLogger('request_logger')
        self.request_logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(f"{self.log_directory}/requests.log", maxBytes=10000000, backupCount=5)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.request_logger.addHandler(handler)

    def log_request(self, request_data):
        with self.lock:
            self.request_logger.info(json.dumps(request_data))

logger = MeterLoggingSystem()

@app.before_request
def before_request():
    g.start_time = datetime.now()

@app.after_request
def after_request(response):
    elapsed = (datetime.now() - g.start_time).total_seconds()
    logger.log_request({'path': request.path, 'method': request.method, 'status': response.status_code, 'time_taken': elapsed})
    return response

# ========== Data Structures ==========
class ReadingStatus(Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    ARCHIVED = "archived"
    ERROR = "error"

@dataclass
class MeterReading:
    reading_id: str
    meter_id: str
    timestamp: datetime
    value: float
    status: ReadingStatus

@dataclass
class ElectricityAccount:
    account_id: str
    meter_id: str
    owner_name: str
    readings: List[MeterReading]

class MeterDataManager:
    def __init__(self):
        self.accounts: Dict[str, ElectricityAccount] = {}
        self.meter_readings: Dict[str, List[MeterReading]] = defaultdict(list)

    def add_reading(self, meter_id: str, value: float):
        reading = MeterReading(
            reading_id=f"READ-{len(self.meter_readings[meter_id]) + 1}",
            meter_id=meter_id,
            timestamp=datetime.now(),
            value=value,
            status=ReadingStatus.RECEIVED
        )
        self.meter_readings[meter_id].append(reading)
        return reading

meter_manager = MeterDataManager()

# ========== Account Registration ==========
@app.route('/register', methods=['POST'])
def register_account():
    data = request.json
    account_id = f"ACC-{len(meter_manager.accounts) + 1}"
    meter_manager.accounts[account_id] = ElectricityAccount(
        account_id=account_id,
        meter_id=data['meter_id'],
        owner_name=data['name'],
        readings=[]
    )
    return jsonify({"message": "Account registered successfully"})

# ========== Meter Reading ==========
@app.route('/meter/<meter_id>/reading', methods=['POST'])
def post_reading(meter_id):
    data = request.json
    reading = meter_manager.add_reading(meter_id, float(data['kwh']))
    return jsonify({"message": "Reading received", "reading": reading.__dict__})

@app.route('/meter/<meter_id>/consumption', methods=['GET'])
def get_consumption(meter_id):
    readings = meter_manager.meter_readings.get(meter_id, [])
    return jsonify({"meter_id": meter_id, "readings": [r.__dict__ for r in readings]})

# ========== Stop Readings for Batch Processing ==========
@app.route('/admin/stop_and_batch', methods=['POST'])
def stop_and_batch():
    return jsonify({"message": "Batch processing executed"})

# ========== Interactive Dashboard ==========
try:
    df = pd.read_csv('Electricity_Merged.csv')
except FileNotFoundError:
    print("Error: 'Electricity_Merged.csv' file not found.")
    exit()

dash_app = Dash(__name__, server=app, routes_pathname_prefix='/dashboard/')

dash_app.layout = html.Div([
    html.H1("Electricity Consumption Dashboard", style={"textAlign": "center"}),
    html.Div("Select a category to view average electricity consumption:", style={"margin": "10px"}),
    dcc.RadioItems(
        options=[{'label': col, 'value': col} for col in ['Region', 'Area', 'Dwelling Type']],
        value='Region',
        id='controls-and-radio-item',
        style={"marginBottom": "20px"}
    ),
    dcc.Dropdown(
        id='year-dropdown',
        options=[{'label': str(year), 'value': year} for year in df['Year'].unique()],
        value=df['Year'].min(),
        style={"marginBottom": "20px", 'width': '50%'}
    ),
    dash_table.DataTable(
        data=df.to_dict('records'),
        page_size=6,
        style_table={'overflowX': 'auto'}
    ),
    dcc.Graph(id='controls-and-graph')
])

@callback(
    Output('controls-and-graph', 'figure'),
    [Input('controls-and-radio-item', 'value'),
     Input('year-dropdown', 'value')]
)
def update_graph(col_chosen, selected_year):
    filtered_df = df[df['Year'] == selected_year]
    fig = px.histogram(
        filtered_df,
        x=col_chosen,
        y="Average kWh per Account",
        histfunc='avg',
        title=f"Average kWh per Account by {col_chosen} in {selected_year}"
    )
    fig.update_layout(bargap=0.2)
    return fig

if __name__ == '__main__':
    app.run(debug=True)
