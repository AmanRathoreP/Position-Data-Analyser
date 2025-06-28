# Author: Aman Rathore

from dash.dependencies import Input, Output, State, ALL
from dash import html, dcc, callback_context
import dash
import base64
import json
import pandas as pd
import dash_bootstrap_components as dbc

from utils.data_processing import get_data_summary, filter_data, extract_time_series, add_metadata_to_list
from utils.plot_utils import create_time_series_plot

def register_filter_callbacks(app):
    """Register callbacks for the data filtering step."""
    
    @app.callback(
        [
            Output("data-summary", "children"),
            Output("bodyparts-container", "children")  # Change from "body-parts-dropdown", "options"
        ],
        [Input("workflow-tabs", "active_tab")],
        [
            State("stored-processed-data", "data"),
            State("stored-raw-data", "data")
        ]
    )
    def update_filter_panel(active_tab, processed_data, raw_data):
        """Update the filter panel with data from the processed JSON (after discontinuity fix)."""
        if active_tab != "tab-filter":
            return "Import data first", []
            
        # Use processed data if available, otherwise fall back to raw data
        data_to_use = processed_data if processed_data is not None else raw_data
        if not data_to_use:
            return "Import data first", []
        
        # Get data summary
        summary = get_data_summary(data_to_use)
        
        # Create data summary display
        summary_html = html.Div([
            html.P(f"Total Frames: {summary.get('num_frames', 'Unknown')}", className="mb-1"),
            html.P(f"Animals Detected: {summary.get('num_animals', 'Unknown')}", className="mb-1"),
            html.P(f"Body Parts Available: {len(summary.get('bodyparts', []))}", className="mb-1"),
        ])
        
        # Create custom bodypart entries with name input and checkbox
        bodypart_items = []
        for bp_idx in range(len(summary.get('bodyparts', []))):
            bodypart_items.append(
                dbc.Row([
                    # Index column
                    dbc.Col(
                        html.Div(f"{bp_idx}", style={"fontWeight": "500"}),
                        width=1
                    ),
                    # Name input column
                    dbc.Col(
                        dbc.Input(
                            id={"type": "bodypart-name", "index": bp_idx},
                            type="text",
                            value=f"Bodypart {bp_idx}",
                            placeholder="Enter name"
                        ),
                        width=8
                    ),
                    # Checkbox column
                    dbc.Col(
                        dbc.Checkbox(
                            id={"type": "bodypart-checkbox", "index": bp_idx},
                            value=True
                        ),
                        width=3,
                        className="d-flex align-items-center justify-content-center"
                    )
                ], 
                className="mb-2 pt-2 pb-2 border-bottom")
            )
        
        # Header row
        header_row = dbc.Row([
            dbc.Col(html.Div("Index", style={"fontWeight": "bold"}), width=1),
            dbc.Col(html.Div("Name", style={"fontWeight": "bold"}), width=8),
            dbc.Col(html.Div("Include", style={"fontWeight": "bold"}), width=3, className="text-center")
        ], className="mb-2 pb-2 border-bottom bg-light")
        
        return summary_html, [header_row] + bodypart_items

    # Update the apply_data_filters callback to use the new data format
    @app.callback(
        [
            Output("filter-preview", "children"),
            Output("filter-preview-plot", "figure"),
            Output("stored-filtered-data", "data"),
            Output("proceed-to-viz-btn", "disabled")
        ],
        [Input("apply-filters-btn", "n_clicks")],
        [
            State("stored-processed-data", "data"),
            State("stored-raw-data", "data"),
            State("num-animals-slider", "value"),
            State("confidence-threshold-slider", "value"),
            State("bodyparts-names-store", "data"),
            State("fps-input", "value"),  # Add FPS input state
            State("workflow-tabs", "active_tab")
        ]
    )
    def apply_data_filters(n_clicks, processed_data, raw_data, num_animals, conf_threshold, bodypart_data, fps, active_tab):
        """Apply filters to the processed or raw data and show preview."""
        if n_clicks is None or active_tab != "tab-filter":
            return "Apply filters to see preview", {}, None, True
            
        # Use processed data if available, otherwise fall back to raw data
        data_to_use = processed_data if processed_data is not None else raw_data
        if not data_to_use:
            return "Apply filters to see preview", {}, None, True
        
        # Extract selected body part indices
        selected_bodyparts = [
            int(idx) for idx, data in bodypart_data.items() 
            if data.get("include") == True
        ]
        
        # Extract bodypart names
        bodypart_names = {
            idx: data.get("name", f"Bodypart {idx}") 
            for idx, data in bodypart_data.items()
        }
        
        # Apply filters
        filtered_data = filter_data(
            data_to_use, 
            num_animals=num_animals, 
            confidence_threshold=conf_threshold,
            selected_bodyparts=selected_bodyparts
        )
        
        # Store complete bodypart data and FPS in the filtered data
        if isinstance(filtered_data, dict) and 'metadata' in filtered_data:
            filtered_data['metadata']['bodypart_names'] = bodypart_data
            filtered_data['metadata']['fps'] = fps  # Store FPS in metadata
        else:
            filtered_data = add_metadata_to_list(filtered_data)
            filtered_data['metadata'] = {
                'bodypart_names': bodypart_data,
                'fps': fps  # Store FPS in metadata
            }
        
        # Create preview info
        original_summary = get_data_summary(data_to_use)
        filtered_summary = get_data_summary(filtered_data)
        
        # Get selected bodypart names for display
        selected_bp_names = [
            bodypart_names.get(str(bp_idx), f"Bodypart {bp_idx}")
            for bp_idx in selected_bodyparts
        ]
        
        preview_html = html.Div([
            html.P("Filtering Results:", className="mb-1"),
            html.P(f"Frames: {filtered_summary.get('num_frames')} (was {original_summary.get('num_frames')})", className="mb-1"),
            html.P(f"Animals: {filtered_summary.get('num_animals')} (limited from {original_summary.get('num_animals')})", className="mb-1"),
            html.P(f"Confidence Threshold: {conf_threshold}", className="mb-1"),
            html.P(f"Selected Body Parts: {', '.join(selected_bp_names)}", className="mb-1")
        ])
        
        # Create preview plot
        figure = {}
        if filtered_data and filtered_summary.get('num_animals', 0) > 0 and selected_bodyparts:
            # Pick the first animal and body part for preview
            animal_idx = 0
            bodypart_idx = selected_bodyparts[0] if selected_bodyparts else 0
            bodypart_name = bodypart_names.get(str(bodypart_idx), f"Bodypart {bodypart_idx}")
            
            # Extract time series and get fps
            df, fps = extract_time_series(filtered_data, animal_idx, bodypart_idx)
            
            # Create plot
            figure = create_time_series_plot(
                df, 
                "x", 
                title=f"Preview: Animal {animal_idx+1}, {bodypart_name} X Position",
                fps=fps
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
    
    @app.callback(
        [Output("confidence-threshold-slider", "value"), 
         Output("confidence-threshold-input", "value")],
        [Input("confidence-threshold-slider", "value"),
         Input("confidence-threshold-input", "value")],
        prevent_initial_call=True
    )
    def sync_confidence_values(slider_value, input_value):
        """Synchronize slider and input values without circular dependency."""
        # Determine which input triggered the callback
        trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        
        # Slider to input
        if trigger_id == "confidence-threshold-slider":
            return slider_value, slider_value
        # Input to slider (with constraints)
        else:
            valid_value = 0.5 if input_value is None else max(0, min(1, input_value))
            return valid_value, valid_value
    
    # Trigger hidden upload component when load button is clicked
    @app.callback(
        Output("upload-config", "filename"),
        [Input("load-config-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def trigger_config_upload(n_clicks):
        """Trigger the hidden upload component when Load Config button is clicked."""
        if n_clicks:
            return None
        raise dash.exceptions.PreventUpdate
    
    # Handle config file upload
    @app.callback(
        [
            Output("num-animals-slider", "value", allow_duplicate=True),
            Output("confidence-threshold-slider", "value", allow_duplicate=True),
            Output("confidence-threshold-input", "value", allow_duplicate=True),
            Output("bodyparts-names-store", "data", allow_duplicate=True)
        ],
        [Input("upload-config", "contents")],
        [
            State("upload-config", "filename"),
            State("stored-processed-data", "data"),
            State("stored-raw-data", "data")
        ],
        prevent_initial_call=True
    )
    def load_config_file(contents, filename, processed_data, raw_data):
        """Load configuration from uploaded JSON file."""
        if contents is None:
            raise dash.exceptions.PreventUpdate
            
        # Use processed data if available, otherwise fall back to raw data
        data_to_use = processed_data if processed_data is not None else raw_data
        
        # Parse the uploaded JSON file
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')
            
            config = json.loads(decoded)
            
            # Extract values from config
            num_animals = config.get("num_animals", 2)
            confidence_threshold = config.get("confidence_threshold", 0.5)
            bodyparts_data = config.get("bodyparts", {})
            
            print(f"Loaded config with {len(bodyparts_data)} bodyparts")
            
            return num_animals, confidence_threshold, confidence_threshold, bodyparts_data
        
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            import traceback
            traceback.print_exc()
            raise dash.exceptions.PreventUpdate
    
    # Save config to file
    @app.callback(
        Output("download-config", "data"),
        [Input("save-config-btn", "n_clicks")],
        [
            State("num-animals-slider", "value"),
            State("confidence-threshold-slider", "value"),
            State("bodyparts-names-store", "data")
        ],
        prevent_initial_call=True
    )
    def save_config_file(n_clicks, num_animals, confidence_threshold, bodyparts_data):
        """Save current configuration to a JSON file."""
        if n_clicks is None:
            raise dash.exceptions.PreventUpdate
        
        # Create config dictionary
        config = {
            "num_animals": num_animals,
            "confidence_threshold": confidence_threshold,
            "bodyparts": bodyparts_data if bodyparts_data else {}
        }
        
        # Return as downloadable JSON file
        return dict(
            content=json.dumps(config, indent=2),
            filename="dlc_filter_config.json",
            type="application/json"
        )
    
    @app.callback(
        Output("upload-config", "contents"),
        [Input("bodyparts-names-store", "data")],
        [State("upload-config", "contents")]
    )
    def reset_upload(data, current_contents):
        """Reset the upload component after loading config."""
        # Only reset if there was content
        if current_contents:
            return None
        raise dash.exceptions.PreventUpdate

    # Update the callback that populates bodypart inputs from store
    @app.callback(
        [Output({"type": "bodypart-name", "index": ALL}, "value"),
         Output({"type": "bodypart-checkbox", "index": ALL}, "value")],
        [Input("bodyparts-names-store", "modified_timestamp")],  # Use modified_timestamp instead of data
        [State("bodyparts-names-store", "data")],
        prevent_initial_call=True
    )
    def update_bodypart_ui_from_store(timestamp, bodyparts_data):
        """Update the bodypart UI components when the store is updated."""
        if not timestamp or not bodyparts_data:
            raise dash.exceptions.PreventUpdate
        
        # Collect all possible indices
        max_index = max([int(idx) for idx in bodyparts_data.keys()]) if bodyparts_data else 0
        
        # Prepare arrays for all possible indices
        names = [""] * (max_index + 1)
        includes = [False] * (max_index + 1)
        
        # Fill in the data we have
        for idx_str, data in bodyparts_data.items():
            idx = int(idx_str)
            if idx < len(names):
                names[idx] = data.get("name", f"Bodypart {idx}")
                includes[idx] = data.get("include", False)
        
        return names, includes

    # Update the callback that updates store from bodypart inputs
    @app.callback(
        Output("bodyparts-names-store", "data", allow_duplicate=True),
        [Input({"type": "bodypart-name", "index": ALL}, "value"),
         Input({"type": "bodypart-checkbox", "index": ALL}, "value")],
        [State("bodyparts-names-store", "modified_timestamp")],
        prevent_initial_call=True  # Add this line
    )
    def update_bodyparts_store(names, includes, timestamp):
        """Update the bodyparts store when inputs change."""
        ctx = callback_context
        
        # Skip this update if it was triggered by the callback above (using timestamp)
        if timestamp and ctx.triggered and ctx.triggered[0]['prop_id'] == "bodyparts-names-store.modified_timestamp":
            raise dash.exceptions.PreventUpdate
        
        # Create data object
        data = {}
        for i, (name, include) in enumerate(zip(names, includes)):
            data[str(i)] = {
                "name": name or f"Bodypart {i}",
                "include": include
            }
        
        return data