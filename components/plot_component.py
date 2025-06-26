# Author: Aman Rathore

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_plot_panel():
    """Create the visualization interface for Step 3."""
    return dbc.Card([
        dbc.CardBody([
            html.H4("Visualize Data", className="card-title"),
            html.P("Generate visualizations from the filtered tracking data."),
            
            # Plot controls
            dbc.Row([
                dbc.Col([
                    html.H5("Plot Controls"),
                    
                    # Plot type selection
                    html.Label("Plot Type:"),
                    dcc.Dropdown(
                        id="plot-type-dropdown",
                        options=[
                            {"label": "X Position Over Time", "value": "time_series_x"},
                            {"label": "Y Position Over Time", "value": "time_series_y"},
                            {"label": "Trajectory (X vs Y)", "value": "trajectory"}
                        ],
                        value="time_series_x",
                        clearable=False,
                        className="mb-3"
                    ),
                    
                    # Animal selection
                    html.Label("Select Animal:"),
                    dcc.Dropdown(
                        id="animal-dropdown",
                        options=[],  # Will be populated by callback
                        className="mb-3"
                    ),
                    
                    # Body part selection
                    html.Label("Select Body Part:"),
                    dcc.Dropdown(
                        id="bodypart-dropdown",
                        options=[],  # Will be populated by callback
                        className="mb-3"
                    ),
                    
                    # Additional plot parameters
                    html.Div(
                        id="plot-parameters",
                        className="mb-3"
                    ),
                    
                    # Generate plot button
                    dbc.Button(
                        "Generate Plot", 
                        id="generate-plot-btn", 
                        color="primary", 
                        className="me-2"
                    ),
                    
                    # Download buttons
                    dbc.Button(
                        "Download Plot", 
                        id="download-plot-btn", 
                        color="secondary", 
                        className="me-2"
                    ),
                    dbc.Button(
                        "Export Data", 
                        id="export-data-btn", 
                        color="secondary"
                    ),
                    
                    # Download components
                    dcc.Download(id="download-plot"),
                    dcc.Download(id="download-data")
                ], width=3),
                
                # Main plot area
                dbc.Col([
                    html.H5("Visualization"),
                    dcc.Loading(
                        id="loading-plot",
                        type="circle",
                        children=[
                            dcc.Graph(
                                id="main-plot", 
                                style={"height": "600px"},
                                figure={}
                            )
                        ]
                    )
                ], width=9)
            ])
        ])
    ])