# Author: Aman Rathore

import dash_bootstrap_components as dbc
from dash import html, dcc

from components.import_component import create_import_panel
from components.filter_component import create_filter_panel
from components.plot_component import create_plot_panel

def create_layout():
    """Create the main layout of the application with the three-step workflow."""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1("Position Data Analyser", className="text-center mb-4"),
                html.Hr(),
            ])
        ]),
        
        # Store components for sharing data between callbacks
        dcc.Store(id="stored-raw-data"),
        dcc.Store(id="stored-filtered-data"),
        dcc.Store(id="current-tab", data="tab-import"),  # Track active tab
        
        # Tabs for the three-step workflow
        dbc.Row([
            dbc.Col([
                dbc.Tabs([
                    dbc.Tab(create_import_panel(), label="Step 1: Import Data", tab_id="tab-import"),
                    dbc.Tab(create_filter_panel(), label="Step 2: Filter Data", tab_id="tab-filter"),
                    dbc.Tab(create_plot_panel(), label="Step 3: Visualize Data", tab_id="tab-plot")
                ], id="workflow-tabs", active_tab="tab-import")
            ])
        ]),
        
        # Footer
        dbc.Row([
            dbc.Col([
                html.Hr(),
                html.P([
                    "© 2025 ", 
                    html.A("Aman Rathore", href="https://amanr.me", target="_blank")
                ], className="text-center")
            ])
        ])
    ], fluid=True)