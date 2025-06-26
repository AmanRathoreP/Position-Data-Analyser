# Author: Aman Rathore

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_import_panel():
    """Create the data import interface for Step 1."""
    return dbc.Card([
        dbc.CardBody([
            html.H4("Import DeepLabCut JSON Data", className="card-title"),
            html.P("Select a JSON file exported from DeepLabCut to begin analysis."),
            
            # File upload component
            dcc.Upload(
                id="upload-data",
                children=html.Div([
                    html.P("Drag and Drop or"),
                    html.Button("Select JSON File", className="btn btn-primary")
                ]),
                style={
                    'width': '100%',
                    'height': '150px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px 0'
                },
                multiple=False
            ),
            
            # File info display
            html.Div(id="file-info"),
            
            # JSON preview
            html.Div([
                html.H5("JSON Preview"),
                dbc.Alert(
                    "No file selected", 
                    color="secondary", 
                    id="json-preview"
                )
            ]),
            
            # Next step button
            dbc.Button(
                "Proceed to Filtering", 
                id="proceed-to-filter-btn", 
                color="primary", 
                className="mt-3",
                disabled=True
            )
        ])
    ])