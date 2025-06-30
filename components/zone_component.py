# Author: Aman Rathore

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_zone_panel():
    """Create the interface for defining and visualizing zones."""
    return dbc.Card([
        dbc.CardBody([
            html.H4("Define Analysis Zones", className="card-title"),
            html.P("Create zones for analysis by defining shapes and their operations."),
            
            dbc.Row([
                # Left column - Controls
                dbc.Col([
                    # Zone Definition
                    html.H5("Zone Definition"),
                    html.P("Define zones using the zone definition language:"),
                    dcc.Textarea(
                        id="zone-definition-input",
                        value="""# Three overlapping circles of varying radii
c1        = (100, 100,  80)    # small circle near bottom-left
c2        = (500, 400, 150)    # large circle in upper center
c3        = (200, 500, 100)    # medium circle near top

# A concave "starburst" polygon
starburst = [(600,540),(660,400),(840,400),(700,300),(760,160),(600,240),(440,160),(500,300),(360,400),(540,400)]

# A convex "diamond" polygon
diamond   = [(600,600),(800,300),(600,0),(400,300)]

# A "donut" at (12,0) with hole
ring_big   = (250, 400, 140)   # outer radius=140
ring_small = (250, 400,  60)   # inner radius=60
donut      = ring_big - ring_small

# Carve holes & chain set-ops
holey     = donut - starburst
combo1    = starburst U diamond
cutout    = combo1 - donut
symdiff1  = cutout ^ c1
mega_zone = symdiff1 U holey

""",
                        style={'width': '100%', 'height': '300px', 'fontFamily': 'monospace'},
                        className="mb-3"
                    ),
                    
                    # Buttons
                    dbc.Button(
                        "Update Zones", 
                        id="update-zones-btn", 
                        color="primary",
                        className="me-2"
                    ),
                    dbc.Button(
                        "Clear", 
                        id="clear-zones-btn", 
                        color="secondary",
                        className="me-2"
                    ),
                    
                    html.Hr(),
                    
                    # Reference Image Upload
                    html.H5("Reference Image", className="mt-3"),
                    html.P("Upload a background image as reference for zone creation:"),
                    dcc.Upload(
                        id='upload-background-image',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select a Reference Image')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        },
                    ),
                    html.Div(id="uploaded-image-name", className="mt-2 mb-3"),
                    
                    # Image display options
                    html.Div([
                        html.Label("Image Opacity:"),
                        dcc.Slider(
                            id="image-opacity-slider",
                            min=0,
                            max=1,
                            step=0.1,
                            value=0.5,
                            marks={i/10: str(i/10) for i in range(0, 11)},
                        )
                    ], className="mt-3"),
                    
                    # Store for zones data
                    dcc.Store(id="zones-data-store"),
                    # Store for background image
                    dcc.Store(id="background-image-store"),
                    
                ], width=5),
                
                # Right column - Visualization
                dbc.Col([
                    html.H5("Zone Visualization"),
                    dcc.Loading(
                        id="loading-zones",
                        type="circle",
                        children=[
                            dcc.Graph(
                                id="zones-plot", 
                                style={"height": "500px"},
                                config={'displayModeBar': True}
                            )
                        ]
                    ),
                    dbc.Alert(
                        id="zones-error",
                        color="danger",
                        is_open=False,
                        dismissable=True,
                        style={"marginTop": "10px"}
                    )
                ], width=7)
            ]),
            
            # Proceed button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "Proceed to Filtering", 
                        id="proceed-to-filter-btn-zones", 
                        color="primary", 
                        className="mt-3",
                    )
                ], width=12, className="d-flex justify-content-end")
            ])
        ])
    ])