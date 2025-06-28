# Author: Aman Rathore

from dash.dependencies import Input, Output, State
from dash import html
import pandas as pd
import json
import numpy as np
import plotly.graph_objs as go

from utils.data_processing import get_data_summary, extract_time_series
from utils.plot_utils import create_time_series_plot, create_trajectory_plot, create_heatmap

def register_plot_callbacks(app):
    """Register callbacks for the visualization step."""
    
    @app.callback(
        [
            Output("animal-dropdown", "options"),
            Output("animal-dropdown", "value"),
            Output("bodypart-dropdown", "options"),
            Output("bodypart-dropdown", "value")
        ],
        [Input("workflow-tabs", "active_tab")],
        [State("stored-filtered-data", "data")]
    )
    def update_plot_options(active_tab, filtered_data):
        """Update the dropdown options when entering the visualization tab."""
        print("Entering update_plot_options")
        print("Filtered data type:", type(filtered_data))
        if active_tab != "tab-plot" or not filtered_data:
            return [], None, [], None
        
        # Handle the case when filtered_data is a JSON string (common when coming from dcc.Store)
        if isinstance(filtered_data, str):
            try:
                filtered_data = json.loads(filtered_data)
            except:
                pass
        
        # Get summary info
        summary = get_data_summary(filtered_data)
        num_animals = summary.get("num_animals", 0)
        
        # Create animal options
        animal_options = [
            {"label": f"Animal {i+1}", "value": i}
            for i in range(num_animals)
        ]
        
        # Extract body part names from metadata
        bodypart_options = []
        
        # Check if we have metadata
        if isinstance(filtered_data, dict) and 'metadata' in filtered_data:
            print("Metadata found:", filtered_data['metadata'])
            bp_names = filtered_data['metadata'].get('bodypart_names', {})
            print("Body part names:", bp_names)
            # Count included body parts
            included_count = 0
            for idx, data in bp_names.items():
                if isinstance(data, dict) and data.get('include') == True:
                    included_count += 1
            print(f"Found {included_count} included body parts")
            
            # Add each selected bodypart to options
            for idx, data in bp_names.items():
                # Only add bodypart if it was included
                if isinstance(data, dict) and data.get('include') == True:
                    name = data.get('name', f"Bodypart {idx}")
                    bodypart_options.append({"label": name, "value": int(idx)})
        else:
            # Fallback - use the data to determine which bodyparts have data
            actual_data = filtered_data.get('data', filtered_data)
            if actual_data and len(actual_data) > 0 and 'bodyparts' in actual_data[0] and len(actual_data[0]['bodyparts']) > 0:
                # For each possible bodypart index
                for bp_idx in range(len(actual_data[0]['bodyparts'][0])):
                    # Check if any frame has non-NaN data for this bodypart
                    has_data = False
                    for frame in actual_data:
                        if len(frame['bodyparts'][0]) > bp_idx:
                            x, y, _ = frame['bodyparts'][0][bp_idx]
                            if not (np.isnan(x) or np.isnan(y)):
                                has_data = True
                                break
                    
                    # Only add bodyparts that have actual data
                    if has_data:
                        bodypart_options.append({"label": f"Bodypart {bp_idx}", "value": bp_idx})
        
        # Print debug info
        print(f"Found {len(bodypart_options)} bodypart options")
        
        # Set default values if options exist
        default_animal = 0 if animal_options else None
        default_bodypart = bodypart_options[0]["value"] if bodypart_options else None
        
        return animal_options, default_animal, bodypart_options, default_bodypart
    
    # Your existing generate_plot callback
    @app.callback(
        Output("main-plot", "figure"),
        [Input("generate-plot-btn", "n_clicks")],
        [
            State("plot-type-dropdown", "value"),
            State("animal-dropdown", "value"), 
            State("bodypart-dropdown", "value"),
            State("stored-filtered-data", "data")
        ]
    )
    def generate_plot(n_clicks, plot_type, animal_idx, bodypart_idx, filtered_data):
        """Generate the plot based on selections."""
        if n_clicks is None or animal_idx is None or bodypart_idx is None:
            return {}
        
        # Handle the case when filtered_data is a JSON string
        if isinstance(filtered_data, str):
            try:
                filtered_data = json.loads(filtered_data)
            except:
                pass
        
        # Get bodypart name for title
        bodypart_name = f"Bodypart {bodypart_idx}"
        
        # Try to get name from metadata
        if isinstance(filtered_data, dict) and filtered_data.get('metadata'):
            bp_names = filtered_data.get('metadata', {}).get('bodypart_names', {})
            if str(bodypart_idx) in bp_names:
                if isinstance(bp_names[str(bodypart_idx)], dict):
                    bodypart_name = bp_names[str(bodypart_idx)].get('name', bodypart_name)
                else:
                    bodypart_name = bp_names[str(bodypart_idx)]
        
        # Extract time series for selected animal and bodypart
        df, fps = extract_time_series(filtered_data, animal_idx, bodypart_idx)
        
        # Generate the appropriate plot
        if plot_type == "time_series_x" or plot_type == "X Position Over Time":
            return create_time_series_plot(
                df, "x", 
                title=f"X Position: Animal {animal_idx+1}, {bodypart_name}",
                fps=fps
            )
        elif plot_type == "time_series_y" or plot_type == "Y Position Over Time":
            return create_time_series_plot(
                df, "y", 
                title=f"Y Position: Animal {animal_idx+1}, {bodypart_name}",
                fps=fps  # Add fps parameter here
            )
        elif plot_type == "trajectory" or plot_type == "Trajectory (X vs Y)":
            return create_trajectory_plot(
                df,
                title=f"Trajectory: Animal {animal_idx+1}, {bodypart_name}",
                fps=fps  # Add fps parameter here
            )
        elif plot_type == "heatmap" or plot_type == "Occupancy Heatmap":
            # Filter out NaN values
            valid_df = df.dropna(subset=['x', 'y'])
            if valid_df.empty:
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title=f"Not enough valid data points for heatmap (Animal {animal_idx+1}, {bodypart_name})",
                    template="plotly_white"
                )
                return empty_fig
                
            return create_heatmap(
                valid_df['x'].values,
                valid_df['y'].values,
                title=f"Occupancy Heatmap: Animal {animal_idx+1}, {bodypart_name}",
                fps=fps  # Add fps parameter here
            )
        
        return {}