import dash_bootstrap_components as dbc
from dash import html, dcc

def create_filter_panel():
    """Create the data filtering interface for Step 2."""
    return dbc.Card([
        dbc.CardBody([
            html.H4("Filter and Clean Data", className="card-title"),
            html.P("Configure filtering options and clean the tracking data."),
            
            # Data info summary
            dbc.Alert(
                "Import data first", 
                color="secondary", 
                id="data-summary"
            ),
            
            # Configuration file controls
            dbc.Row([
                dbc.Col([
                    html.H5("Configuration:", className="mb-2"),
                    html.Div([
                        # Changed from justify-content-between to justify-content-start
                        # and added me-2 to the first button for spacing
                        html.Div([
                            dcc.Upload(
                                id="upload-config",
                                children=dbc.Button(
                                    "Load Config", 
                                    id="load-config-btn", 
                                    color="secondary",
                                    className="me-2"  # Add margin to the right of the first button
                                ),
                                multiple=False
                            ),
                            dbc.Button(
                                "Download Config", 
                                id="save-config-btn", 
                                color="secondary"
                            ),
                        ], className="d-flex justify-content-start w-100"),  # Changed from justify-content-between to justify-content-start
                        dcc.Download(id="download-config"),
                    ], className="mb-3"),
                ], width=12),
            ]),
            
            # Filtering options
            dbc.Row([
                dbc.Col([
                    html.H5("Filtering Options"),
                    
                    # Number of animals
                    html.Label("Number of Animals to Include:"),
                    dcc.Slider(
                        id="num-animals-slider",
                        min=1,
                        max=10,
                        step=1,
                        value=2,
                        marks={i: str(i) for i in range(1, 11)},
                        className="mb-4"
                    ),
                    
                    # Confidence threshold with more precision
                    html.Label("Confidence Threshold:"),
                    html.Div([
                        dcc.Slider(
                            id="confidence-threshold-slider",
                            min=0,
                            max=1,
                            step=0.001,
                            value=0.5,
                            marks={i/10: str(i/10) for i in range(0, 11)},
                            className="mb-2"
                        ),
                        # Add a numeric input for precise control
                        dbc.Row([
                            dbc.Col([
                                html.Label("Exact value:"),
                            ], width=4),
                            dbc.Col([
                                dbc.Input(
                                    id="confidence-threshold-input",
                                    type="number",
                                    min=0,
                                    max=1,
                                    step=0.001,
                                    value=0.5,
                                    style={"width": "100%"}
                                ),
                            ], width=8)
                        ], className="mb-4")
                    ]),
                    
                    # Add FPS input field
                    html.Label("Frames Per Second (FPS):"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="fps-input",
                                type="number",
                                min=1,
                                max=1000,
                                step=1,
                                value=30,
                                placeholder="Enter FPS (e.g., 30)",
                                style={"width": "100%"}
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Small("Used to convert frames to time units in plots", className="text-muted")
                        ], width=6)
                    ], className="mb-4"),
                    
                    # Body parts of interest - custom component with checkboxes
                    html.Label("Body Parts of Interest:", className="mt-3"),
                    html.P("Assign names to body parts and select which ones to include:", className="mb-2"),
                    html.Div(
                        id="bodyparts-container",
                        className="mb-4",
                        style={"maxHeight": "350px", "overflowY": "auto", "border": "1px solid #dee2e6", "borderRadius": "5px", "padding": "10px"}
                    ),
                    
                    # Store for bodypart names and selection states
                    dcc.Store(id="bodyparts-names-store"),
                    
                    # Filter button
                    dbc.Button(
                        "Apply Filters", 
                        id="apply-filters-btn", 
                        color="primary", 
                        className="mb-4"
                    )
                ], width=6),
                
                # Preview of filtered data
                dbc.Col([
                    html.H5("Preview"),
                    dbc.Alert(
                        "Apply filters to see preview", 
                        color="secondary", 
                        id="filter-preview"
                    ),
                    # Small plot to visualize the effect of filtering
                    dcc.Graph(id="filter-preview-plot", style={"height": "300px"})
                ], width=6)
            ]),
            
            # Next step button
            dbc.Button(
                "Proceed to Visualization", 
                id="proceed-to-viz-btn", 
                color="primary", 
                className="mt-3",
                disabled=True
            ),
            
            # JavaScript to handle file upload click
            html.Script('''
            document.addEventListener('DOMContentLoaded', function() {
                const loadBtn = document.getElementById('load-config-btn');
                const upload = document.getElementById('upload-config');
                
                if(loadBtn && upload) {
                    loadBtn.addEventListener('click', function() {
                        upload.click();
                    });
                }
            });
            ''')
        ])
    ])


def register_filter_callbacks(app):
    """Register callbacks for the data filtering step."""
    
    @app.callback(
        [
            Output("data-summary", "children"),
            Output("body-parts-dropdown", "options")
        ],
        [Input("workflow-tabs", "active_tab")],
        [State("stored-raw-data", "data")]
    )
    def update_filter_panel(active_tab, raw_data):
        """Update the filter panel with data from the imported JSON."""
        if active_tab != "tab-filter" or not raw_data:
            return "Import data first", []
        
        # Get data summary
        summary = get_data_summary(raw_data)
        
        # Create data summary display
        summary_html = html.Div([
            html.P(f"Total Frames: {summary.get('num_frames', 'Unknown')}", className="mb-1"),
            html.P(f"Animals Detected: {summary.get('num_animals', 'Unknown')}", className="mb-1"),
            html.P(f"Body Parts Available: {len(summary.get('bodyparts', []))}", className="mb-1"),
        ])
        
        # Create body parts options
        bp_options = [
            {"label": f"Bodypart {bp_idx}", "value": bp_idx}
            for bp_idx in range(len(summary.get('bodyparts', [])))
        ]
        
        return summary_html, bp_options
    
    @app.callback(
        [
            Output("filter-preview", "children"),
            Output("filter-preview-plot", "figure"),
            Output("stored-filtered-data", "data"),
            Output("proceed-to-viz-btn", "disabled")
        ],
        [Input("apply-filters-btn", "n_clicks")],
        [
            State("stored-raw-data", "data"),
            State("num-animals-slider", "value"),
            State("confidence-threshold-slider", "value"),
            State("body-parts-dropdown", "value"),
            State("workflow-tabs", "active_tab")
        ]
    )
    def apply_data_filters(n_clicks, raw_data, num_animals, conf_threshold, selected_bodyparts, active_tab):
        """Apply filters to the raw data and show preview."""
        if n_clicks is None or not raw_data or active_tab != "tab-filter":
            return "Apply filters to see preview", {}, None, True
        
        # Apply filters
        filtered_data = filter_data(
            raw_data, 
            num_animals=num_animals, 
            confidence_threshold=conf_threshold,
            selected_bodyparts=selected_bodyparts
        )
        
        # Create preview info
        original_summary = get_data_summary(raw_data)
        filtered_summary = get_data_summary(filtered_data)
        
        preview_html = html.Div([
            html.P("Filtering Results:", className="mb-1"),
            html.P(f"Frames: {filtered_summary.get('num_frames')} (was {original_summary.get('num_frames')})", className="mb-1"),
            html.P(f"Animals: {filtered_summary.get('num_animals')} (limited from {original_summary.get('num_animals')})", className="mb-1"),
            html.P(f"Confidence Threshold: {conf_threshold}", className="mb-1"),
            html.P(f"Selected Body Parts: {len(selected_bodyparts) if selected_bodyparts else 'All'}", className="mb-1")
        ])
        
        # Create preview plot
        figure = {}
        if filtered_data and filtered_summary.get('num_animals', 0) > 0:
            # Pick the first animal and body part for preview
            animal_idx = 0
            bodypart_idx = selected_bodyparts[0] if selected_bodyparts else 0
            
            # Extract time series
            df = extract_time_series(filtered_data, animal_idx, bodypart_idx)
            
            # Create plot
            figure = create_time_series_plot(
                df, 
                "x", 
                title=f"Preview: Animal {animal_idx+1}, Bodypart {bodypart_idx+1} X Position"
            )
        
        return preview_html, figure, filtered_data, False
    
    @app.callback(
        Output("workflow-tabs", "active_tab", allow_duplicate=True),
        [Input("proceed-to-viz-btn", "n_clicks")],
        [State("stored-filtered-data", "data")],
        prevent_initial_call=True
    )
    def proceed_to_visualization(n_clicks, filtered_data):
        """Proceed to the visualization tab when the button is clicked."""
        if n_clicks is None or not filtered_data:
            return "tab-filter"
        
        return "tab-plot"