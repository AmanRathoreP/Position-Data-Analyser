# Author: Aman Rathore

from dash.dependencies import Input, Output, State, ALL  # Add ALL here
from dash import html, dcc, callback_context  # Add callback_context here
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

    # Add this callback to collect bodypart names and selection states
    @app.callback(
        Output("bodyparts-names-store", "data"),
        [Input({"type": "bodypart-name", "index": ALL}, "value"),
         Input({"type": "bodypart-checkbox", "index": ALL}, "value")]
    )
    def update_bodyparts_names(names, checkboxes):
        """Store the body part names and selection states."""
        if not names or not checkboxes:
            return {}
        
        # Create a dictionary with all bodypart data
        bodyparts_data = {}
        for i in range(len(names)):
            idx = i  # The index within the inputs list matches the bodypart index
            bodyparts_data[str(idx)] = {
                "name": names[i],
                "include": checkboxes[i]
            }
        
        return bodyparts_data
    
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
            State("stored-raw-data", "data"),
            State("num-animals-slider", "value"),
            State("confidence-threshold-slider", "value"),
            State("bodyparts-names-store", "data"),  # Change from "body-parts-dropdown", "value"
            State("workflow-tabs", "active_tab")
        ]
    )
    def apply_data_filters(n_clicks, raw_data, num_animals, conf_threshold, bodypart_data, active_tab):
        """Apply filters to the raw data and show preview."""
        if n_clicks is None or not raw_data or active_tab != "tab-filter":
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
            raw_data, 
            num_animals=num_animals, 
            confidence_threshold=conf_threshold,
            selected_bodyparts=selected_bodyparts
        )
        
        # Store complete bodypart data in the filtered data
        if isinstance(filtered_data, dict) and 'metadata' in filtered_data:
            # It's already in the right format, just update the metadata
            filtered_data['metadata'] = {'bodypart_names': bodypart_data}  # Use bodypart_data instead of bodypart_names
        else:
            # It's not in the right format, convert it
            filtered_data = add_metadata_to_list(filtered_data)
            filtered_data['metadata'] = {'bodypart_names': bodypart_data}  # Use bodypart_data instead of bodypart_names
        
        # Create preview info
        original_summary = get_data_summary(raw_data)
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
            
            # Extract time series
            df = extract_time_series(filtered_data, animal_idx, bodypart_idx)
            
            # Create plot
            figure = create_time_series_plot(
                df, 
                "x", 
                title=f"Preview: Animal {animal_idx+1}, {bodypart_name} X Position"
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