import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import random
import threading
import dash_bootstrap_components as dbc

# Constants
INFLUXDB_URL = "http://universe.phys.unm.edu:8086"
INFLUXDB_TOKEN = "ishf4rkO91al90y4WAJKSiYNBhLri5AhjdX1TKg-J-wmSPL3QqQJF61ghEFmQ-AamdT6ptaBLzKMlf7LCBrfRg=="
INFLUXDB_ORG = "demo"
INFLUXDB_BUCKET = "demo"

# Function to create a client with retries
def create_influxdb_client():
    retries = 5
    while retries > 0:
        try:
            client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
            return client
        except Exception as e:
            print(f"Failed to connect to InfluxDB, retrying... ({retries} retries left)")
            time.sleep(5)
            retries -= 1
    raise Exception("Could not connect to InfluxDB after multiple retries")

# Create a client
client = create_influxdb_client()
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

# Function to generate random data
def log_data():
    while True:
        power = random.uniform(-30.0, 0.0)  # Random power values in dBm
        point = Point("power_measurement") \
            .tag("channel", "channel_1") \
            .field("power", power)
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"Logged: channel=channel_1, power={power:.2f} dBm")
        time.sleep(10)  # log every 10 seconds

# Start logging data in a separate thread
logging_thread = threading.Thread(target=log_data)
logging_thread.daemon = True
logging_thread.start()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("InfluxDB Power Measurement Time Series"),
    dcc.Graph(id="time-series-plot"),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # Update every 10 seconds
        n_intervals=0
    )
])

@app.callback(
    Output('time-series-plot', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_time_series_plot(n):
    # Query data from InfluxDB
    query = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "power_measurement" and r.channel == "channel_1")'
    result = query_api.query(org=INFLUXDB_ORG, query=query)
    
    # Convert to DataFrame
    data = []
    for table in result:
        for record in table.records:
            data.append((record.get_time(), record.get_field(), record.get_value()))

    df = pd.DataFrame(data, columns=["time", "field", "value"])
    
    # Create time series plot
    fig = go.Figure(data=go.Scatter(
        x=df['time'],
        y=df['value'],
        mode='lines+markers'
    ))

    fig.update_layout(
        title="Power Measurements Time Series",
        xaxis_title="Time",
        yaxis_title="Power (dBm)"
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
