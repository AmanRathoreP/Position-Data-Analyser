# Author: Aman Rathore
# Contact: amanr.me | amanrathore9753 <at> gmail <dot> com
# Created on: Wednesday, June 25, 2025 at 21:35

from dash import Dash
import dash_bootstrap_components as dbc

# Initialize the Dash app with Bootstrap
app = Dash(__name__, 
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])

server = app.server
app.title = "Position Data Analyser"