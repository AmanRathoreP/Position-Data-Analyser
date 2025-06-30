# Author: Aman Rathore

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_discontinuity_panel():
    """Create the interface for handling data discontinuities."""
    return dbc.Card([
        dbc.CardBody([
            html.H4("Remove Data Discontinuities", className="card-title"),
            html.P("Detect and fix missing or discontinuous tracking data."),
            
            # Animal selection checkboxes
            html.Div([
                html.H5("Select Animals to Process", className="mb-3"),  # Removed text-center
                dbc.Row([
                    dbc.Col([
                        dbc.Checklist(
                            options=[
                                {"label": f"Animal {i+1}", "value": i} for i in range(10)
                            ],
                            value=[0],  # Default: first animal selected
                            id="animal-selection-checklist",
                            inline=True,
                            switch=True,
                            className="d-flex flex-wrap"  # Removed justify-content-center
                        )
                    ], width=12)
                ], className="mb-3")
            ]),
            
            # Data summary
            html.Div([
                html.H5("Data Summary"),
                html.Div(id="discontinuity-data-summary", className="mb-3")
            ]),
            
            # Settings for discontinuity detection and fixing
            dbc.Row([
                dbc.Col([
                    html.H5("Settings"),
                    
                    # Choose interpolation method
                    html.Label("Interpolation Method:"),
                    dcc.Dropdown(
                        id="interpolation-method",
                        options=[
                            {"label": "Linear Interpolation", "value": "linear"},
                            {"label": "Nearest Point", "value": "nearest"}
                        ],
                        value="linear",
                        className="mb-3"
                    ),
                    
                    # Max gap size to interpolate
                    html.Label("Maximum Gap Size to Interpolate (frames):"),
                    dcc.Slider(
                        id="max-gap-slider",
                        min=1,
                        max=150,
                        step=1,
                        value=100,
                        marks={i: str(i) for i in [1, 25, 50, 75, 100, 125, 150]},
                        className="mb-3"
                    ),
                    
                    # Add confidence value for interpolated points
                    html.Label("Confidence Value for Interpolated Points:"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="interpolation-confidence-input",
                                type="number",
                                min=0,
                                max=1,
                                step=0.01,
                                value=0.51,
                                style={"width": "100%"}
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Tooltip(
                                "Value 0.51 helps identify interpolated points internally. When exporting, all points are normalized to 1.0.",
                                target="interpolation-confidence-input",
                                placement="right"
                            )
                        ], width=6)
                    ], className="mb-3"),
                    
                    # Apply button
                    dbc.Button(
                        "Detect and Fix Discontinuities",
                        id="fix-discontinuities-btn",
                        color="primary",
                        className="mt-2"
                    )
                ], width=6),
                
                # Preview column
                dbc.Col([
                    html.H5("Preview"),
                    dbc.Alert(
                        "Click 'Detect and Fix Discontinuities' to see preview",
                        color="secondary",
                        id="discontinuity-preview"
                    ),
                    # Preview plot showing before and after
                    dcc.Graph(id="discontinuity-preview-plot", style={"height": "300px"})
                ], width=6)
            ]),
            
            # Export option
            dbc.Row([
                dbc.Col([
                    html.H5("Export Processed Data"),
                    dbc.Button(
                        "Export Processed JSON",
                        id="export-processed-json-btn",
                        color="secondary",
                        className="me-2"
                    ),
                    dcc.Download(id="download-processed-json")
                ])
            ], className="mt-3"),
            
            # Next step button
            dbc.Button(
                "Proceed to Zones",
                id="proceed-to-zones-btn-discontinuity",
                color="primary",
                className="mt-3",
                disabled=True
            )
        ])
    ])