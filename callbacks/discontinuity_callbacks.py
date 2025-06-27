# Author: Aman Rathore

import dash
from dash import html, dcc, Input, Output, State, callback_context
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import base64
from datetime import datetime
from scipy import interpolate
import copy

from utils.data_processing import get_data_summary

def register_discontinuity_callbacks(app):
    """Register callbacks for the discontinuity removal step."""
    
    @app.callback(
        [
            Output("discontinuity-data-summary", "children"),
            Output("discontinuity-preview", "children"),
            Output("discontinuity-preview-plot", "figure"),
        ],
        [Input("workflow-tabs", "active_tab")],
        [State("stored-raw-data", "data")]
    )
    def update_discontinuity_panel(active_tab, raw_data):
        """Update the discontinuity panel with data from the imported JSON."""
        if active_tab != "tab-discontinuity" or not raw_data:
            empty_fig = go.Figure()
            empty_fig.update_layout(title="No data to display")
            return "Import data first", "No data to display", empty_fig
        
        # Get data summary
        summary = get_data_summary(raw_data)
        
        # Create data summary display
        summary_html = html.Div([
            html.P(f"Total Frames: {summary.get('num_frames', 'Unknown')}", className="mb-1"),
            html.P(f"Animals Detected: {summary.get('num_animals', 'Unknown')}", className="mb-1"),
            html.P(f"Body Parts Available: {len(summary.get('bodyparts', []))}", className="mb-1"),
        ])
        
        # Calculate initial discontinuities
        discontinuities = detect_discontinuities(raw_data)
        
        preview_text = html.Div([
            html.P(f"Detected {len(discontinuities)} potential discontinuities.", className="mb-1"),
            html.P("Use the settings on the left to fix these issues.", className="mb-1"),
        ])
        
        # Create empty figure (will be filled when user clicks the fix button)
        fig = go.Figure()
        fig.update_layout(
            title="Click 'Detect and Fix Discontinuities' to see data preview",
            xaxis_title="Frame",
            yaxis_title="Position"
        )
        
        return summary_html, preview_text, fig
    
    @app.callback(
        [
            Output("discontinuity-preview-plot", "figure", allow_duplicate=True),
            Output("discontinuity-preview", "children", allow_duplicate=True),
            Output("stored-processed-data", "data"),
            Output("proceed-to-filter-btn-discontinuity", "disabled")
        ],
        [Input("fix-discontinuities-btn", "n_clicks")],
        [
            State("stored-raw-data", "data"),
            State("interpolation-method", "value"),
            State("max-gap-slider", "value"),
            State("animal-selection-checklist", "value"),
            State("interpolation-confidence-input", "value")  # Add this new state
        ],
        prevent_initial_call=True
    )
    def fix_dis_discontinuities(n_clicks, raw_data, method, max_gap, selected_animals, interp_confidence):
        """Fix discontinuities in the data based on user settings and selected animals."""
        if n_clicks is None or not raw_data:
            raise dash.exceptions.PreventUpdate
            
        # Use default value if input is invalid
        if interp_confidence is None or not (0 <= interp_confidence <= 1):
            interp_confidence = 0.51
            
        # Detect discontinuities in the data (only for selected animals)
        discontinuities = detect_discontinuities(raw_data, selected_animals)
        
        # Fix discontinuities based on chosen method and confidence
        processed_data, fixed_count_discontinuities, max_gap_found = fix_data_discontinuities(
            raw_data, discontinuities, method, max_gap, interp_confidence
        )
        
        # Store interpolation confidence in metadata for future reference
        if isinstance(processed_data, dict) and 'metadata' in processed_data:
            processed_data['metadata']['interp_confidence'] = interp_confidence
        elif isinstance(processed_data, dict):
            processed_data['metadata'] = {'interp_confidence': interp_confidence}
        
        # Create preview plot of original vs. processed data
        # Pick the first selected animal for demonstration
        animal_idx = selected_animals[0] if selected_animals else 0
        bodypart_idx = 0
        
        fig = make_subplots(rows=2, cols=1, 
                    subplot_titles=["X Position", "Y Position"],
                    shared_xaxes=True)
        
        # Extract original data with gaps
        x_orig, y_orig, frames = extract_trajectory(raw_data, animal_idx, bodypart_idx)
        
        # Only extract fixed points if there are actual discontinuities
        x_fixed = []
        y_fixed = []
        frames_fixed = []
        
        # Extract interpolated points, passing the custom confidence value
        if discontinuities:
            x_fixed, y_fixed, frames_fixed = extract_fixed_points(
                raw_data, processed_data, animal_idx, bodypart_idx, interp_confidence
            )
        
        # Plot X trajectory - Original data as blue points
        fig.add_trace(
            go.Scatter(
                x=frames, 
                y=x_orig, 
                mode='markers', 
                name='Original X', 
                marker=dict(size=6, color='blue')
            ),
            row=1, col=1
        )
        
        # Only plot interpolated points if we found discontinuities
        if discontinuities and x_fixed:
            fig.add_trace(
                go.Scatter(
                    x=frames_fixed, 
                    y=x_fixed, 
                    mode='markers', 
                    name='Interpolated X', 
                    marker=dict(size=8, color='red', symbol='diamond')
                ),
                row=1, col=1
            )
        
        # Plot Y trajectory - Original data as blue points
        fig.add_trace(
            go.Scatter(
                x=frames, 
                y=y_orig, 
                mode='markers', 
                name='Original Y', 
                marker=dict(size=6, color='blue')
            ),
            row=2, col=1
        )
        
        # Only plot interpolated points if we found discontinuities
        if discontinuities and y_fixed:
            fig.add_trace(
                go.Scatter(
                    x=frames_fixed, 
                    y=y_fixed, 
                    mode='markers', 
                    name='Interpolated Y', 
                    marker=dict(size=8, color='red', symbol='diamond')
                ),
                row=2, col=1
            )
        
        # Update layout with better visibility for scatter points
        fig.update_layout(
            height=500,
            title=f"Animal {animal_idx+1}, Bodypart {bodypart_idx+1} Trajectory",
            legend=dict(orientation="v", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Count previously interpolated points
        fixed_points_count = count_fixed_points(raw_data, processed_data)
        
        # Create summary text with more detailed information
        preview_text = html.Div([
            html.P(f"Detected {len(discontinuities)} discontinuities in {len(selected_animals)} selected animals.", className="mb-1"),
            html.P(f"Fixed {fixed_count_discontinuities} of {len(discontinuities)} discontinuities.", className="mb-1"),
            html.P(f"Maximum gap found: {max_gap_found} frames (limit set to: {max_gap} frames)", className="mb-1")
        ])
        
        # Return the figure, preview text, processed data, and enable the proceed button
        return fig, preview_text, processed_data, False
    
    # Add new callback for the "Proceed to Filtering" button
    @app.callback(
        Output("workflow-tabs", "active_tab", allow_duplicate=True),
        [Input("proceed-to-filter-btn-discontinuity", "n_clicks")],
        [State("stored-processed-data", "data")],
        prevent_initial_call=True
    )
    def proceed_to_filtering(n_clicks, processed_data):
        """Proceed to the filter tab when the button is clicked."""
        if n_clicks is None or not processed_data:
            raise dash.exceptions.PreventUpdate
        
        return "tab-filter"
    
    @app.callback(
        Output("download-processed-json", "data"),
        [Input("export-processed-json-btn", "n_clicks")],
        [State("stored-processed-data", "data")],
        prevent_initial_call=True
    )
    def export_processed_json(n_clicks, processed_data):
        """Export the processed data as a JSON file."""
        if n_clicks is None or not processed_data:
            raise dash.exceptions.PreventUpdate
            
        # Create a deep copy to avoid modifying the stored data
        export_data = copy.deepcopy(processed_data)
        
        # Get the metadata to see if we stored the interpolation confidence
        interp_confidence = 0.51  # Default value to look for
        if isinstance(export_data, dict) and 'metadata' in export_data:
            interp_confidence = export_data['metadata'].get('interp_confidence', 0.51)
        
        # Normalize all confidence values - treat interpolated points as regular points
        if isinstance(export_data, dict) and 'data' in export_data:
            frames = export_data['data']
            for frame in frames:
                if 'bodyparts' in frame:
                    for animal_data in frame['bodyparts']:
                        for i in range(len(animal_data)):
                            x, y, conf = animal_data[i]
                            # Convert interpolated confidence value to regular confidence (1.0)
                            if abs(conf - interp_confidence) < 1e-6:
                                animal_data[i] = [x, y, 1.0]
        
        # Create filename with date/time
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_data_{now}.json"
        
        # Return as downloadable JSON file
        return dict(
            content=json.dumps(export_data, indent=2),
            filename=filename,
            type="application/json"
        )
    
    @app.callback(
        Output("animal-selection-checklist", "options"),
        [Input("workflow-tabs", "active_tab")],
        [State("stored-raw-data", "data")]
    )
    def update_animal_options(active_tab, raw_data):
        """Update the animal selection options based on imported data."""
        if active_tab != "tab-discontinuity" or not raw_data:
            # Default options when no data - all enabled but will show warning
            return [{"label": f"Animal {i+1}", "value": i, "disabled": False} for i in range(10)]
        
        # Count actual animals in the data
        num_animals = 0
        if isinstance(raw_data, dict) and 'data' in raw_data and len(raw_data['data']) > 0:
            if 'bodyparts' in raw_data['data'][0]:
                num_animals = len(raw_data['data'][0]['bodyparts'])
        
        # Create options with all animals enabled
        options = []
        for i in range(10):
            # Add an indicator for real animals but don't disable any options
            if i < num_animals:
                # For animals that exist in the data
                options.append({"label": f"Animal {i+1}", "value": i, "disabled": False})
            else:
                # For animals that don't exist in the data
                options.append({"label": f"Animal {i+1}", "value": i, "disabled": False})
        
        return options

    @app.callback(
        Output("animal-selection-checklist", "value"),
        [Input("animal-selection-checklist", "options")],
        [State("animal-selection-checklist", "value")]
    )
    def update_default_selected_animals(options, current_value):
        """Update the default selected animals when options change."""
        # Always select only the first animal by default
        if not current_value:
            return [0]  # Select the first animal by default
        
        # Keep user's selection if they've made one
        return current_value
        


def detect_discontinuities(data, selected_animals=None):
    """
    Detect discontinuities in the tracking data for selected animals only.
    Returns a list of discontinuities with format:
    [(animal_idx, bodypart_idx, start_frame, end_frame), ...]
    
    Special handling: if any bodypart has confidence = -1, the entire frame 
    is considered discontinuous for that animal and counted only once.
    """
    discontinuities = []
    
    # Extract actual data from data wrapper if needed
    if isinstance(data, dict) and 'data' in data:
        frames = data['data']
    else:
        frames = data
    
    # If no data, return empty list
    if not frames or not isinstance(frames, list) or len(frames) == 0:
        return discontinuities
    
    # Go through each animal and bodypart
    num_animals = 0
    num_bodyparts = 0
    
    # Determine structure
    if 'bodyparts' in frames[0]:
        bodyparts_data = frames[0]['bodyparts']
        num_animals = len(bodyparts_data)
        if num_animals > 0:
            num_bodyparts = len(bodyparts_data[0])
    
    # Default to all animals if none selected
    if selected_animals is None or len(selected_animals) == 0:
        selected_animals = list(range(num_animals))
    
    # For each selected animal, detect frame-level discontinuities
    for animal_idx in selected_animals:
        if animal_idx >= num_animals:
            continue
            
        # Track frame-level discontinuities for this animal
        current_frame_gap = None
        frame_level_discontinuities = []
        
        # First pass: identify frames where entire animal data is discontinuous (any bodypart has conf = -1)
        for frame_idx, frame in enumerate(frames):
            if 'bodyparts' not in frame or len(frame['bodyparts']) <= animal_idx:
                continue
                
            animal_data = frame['bodyparts'][animal_idx]
            
            # Check if any bodypart has confidence = -1, indicating entire frame discontinuity
            frame_is_discontinuous = False
            for bodypart_idx in range(min(num_bodyparts, len(animal_data))):
                if bodypart_idx < len(animal_data):
                    x, y, conf = animal_data[bodypart_idx]
                    if conf == -1:
                        frame_is_discontinuous = True
                        break
            
            if frame_is_discontinuous:
                # Start a new frame-level gap if not already in one
                if current_frame_gap is None:
                    current_frame_gap = (animal_idx, -1, frame_idx, frame_idx)  # Use -1 to indicate frame-level
            else:
                # End the current frame-level gap if we were in one
                if current_frame_gap is not None:
                    animal, _, start, _ = current_frame_gap
                    frame_level_discontinuities.append((animal, -1, start, frame_idx - 1))
                    current_frame_gap = None
        
        # Handle case where frame-level gap extends to the end
        if current_frame_gap is not None:
            animal, _, start, _ = current_frame_gap
            frame_level_discontinuities.append((animal, -1, start, len(frames) - 1))
        
        # Add frame-level discontinuities to main list
        discontinuities.extend(frame_level_discontinuities)
            
        # For each bodypart, detect normal discontinuities (but skip frames marked as frame-level discontinuous)
        frame_level_disc_frames = set()
        for _, _, start, end in frame_level_discontinuities:
            for f in range(start, end + 1):
                frame_level_disc_frames.add(f)
        
        for bodypart_idx in range(num_bodyparts):
            current_gap = None
            
            for frame_idx, frame in enumerate(frames):
                # Skip frames already counted as frame-level discontinuous
                if frame_idx in frame_level_disc_frames:
                    continue
                    
                if 'bodyparts' not in frame or len(frame['bodyparts']) <= animal_idx:
                    continue
                    
                animal_data = frame['bodyparts'][animal_idx]
                if len(animal_data) <= bodypart_idx:
                    continue
                
                # Get position and confidence
                x, y, conf = animal_data[bodypart_idx]
                
                # For non-frame-level discontinuities, only check for NaN values (conf = -1 already handled above)
                is_discontinuity = np.isnan(x) or np.isnan(y)
                
                if is_discontinuity:
                    # Start a new gap if not already in one
                    if current_gap is None:
                        current_gap = (animal_idx, bodypart_idx, frame_idx, frame_idx)
                else:
                    # End the current gap if we were in one
                    if current_gap is not None:
                        animal, bodypart, start, _ = current_gap
                        discontinuities.append((animal, bodypart, start, frame_idx - 1))
                        current_gap = None
            
            # Handle case where gap extends to the end of the sequence
            if current_gap is not None:
                animal, bodypart, start, _ = current_gap
                discontinuities.append((animal, bodypart, start, len(frames) - 1))
    
    return discontinuities


def fix_data_discontinuities(data, discontinuities, method="linear", max_gap=10, interp_confidence=0.51):
    """
    Fix discontinuities in the data using the specified interpolation method.
    Only interpolates frames where original data is missing or has low confidence.
    Returns the processed data and stats about fixed discontinuities.
    
    Parameters:
    -----------
    interp_confidence : float
        The confidence value to assign to interpolated points (default: 0.51)
    """
    # Create a deep copy of the data to avoid modifying the original
    if isinstance(data, dict) and 'data' in data:
        processed_data = {
            'data': [frame.copy() for frame in data['data']],
            'metadata': data.get('metadata', {}).copy()
        }
        frames = processed_data['data']
    else:
        processed_data = [frame.copy() for frame in data]
        frames = processed_data
    
    # Stats tracking
    fixed_discontinuities = 0
    max_gap_found = 0
    
    # Process each discontinuity
    for animal_idx, bodypart_idx, start_frame, end_frame in discontinuities:
        # Calculate gap size and track maximum
        gap_size = end_frame - start_frame + 1
        max_gap_found = max(max_gap_found, gap_size)
        
        # Skip if gap is too large
        if gap_size > max_gap:
            continue
            
        # Find valid points before and after the gap
        before_frame = start_frame - 1
        after_frame = end_frame + 1
        
        # Skip if we don't have valid points before or after
        if before_frame < 0 or after_frame >= len(frames):
            continue
        
        # Handle frame-level discontinuity (bodypart_idx = -1)
        if bodypart_idx == -1:
            # For frame-level discontinuities, we need to fix all bodyparts in these frames
            num_bodyparts = 0
            if ('bodyparts' in frames[0] and 
                len(frames[0]['bodyparts']) > animal_idx and 
                len(frames[0]['bodyparts'][animal_idx]) > 0):
                num_bodyparts = len(frames[0]['bodyparts'][animal_idx])
            
            # Fix each bodypart separately within the frame-level discontinuity
            frame_fixed = False
            for bp_idx in range(num_bodyparts):
                # Get positions before and after the gap for this bodypart
                before_x, before_y = None, None
                after_x, after_y = None, None
                
                # Look for valid data point before gap
                frame_ptr = before_frame
                while frame_ptr >= 0:
                    if ('bodyparts' in frames[frame_ptr] and 
                        len(frames[frame_ptr]['bodyparts']) > animal_idx and
                        len(frames[frame_ptr]['bodyparts'][animal_idx]) > bp_idx):
                        
                        x, y, conf = frames[frame_ptr]['bodyparts'][animal_idx][bp_idx]
                        if not (np.isnan(x) or np.isnan(y) or conf == -1):
                            before_x, before_y = x, y
                            break
                    frame_ptr -= 1
                
                # Look for valid data point after gap
                frame_ptr = after_frame
                while frame_ptr < len(frames):
                    if ('bodyparts' in frames[frame_ptr] and 
                        len(frames[frame_ptr]['bodyparts']) > animal_idx and
                        len(frames[frame_ptr]['bodyparts'][animal_idx]) > bp_idx):
                        
                        x, y, conf = frames[frame_ptr]['bodyparts'][animal_idx][bp_idx]
                        if not (np.isnan(x) or np.isnan(y) or conf == -1):
                            after_x, after_y = x, y
                            break
                    frame_ptr += 1
                
                # Skip if we still don't have valid points before or after
                if before_x is None or after_x is None:
                    continue
                
                # Interpolate each frame in the gap for this bodypart
                for frame_idx in range(start_frame, end_frame + 1):
                    if ('bodyparts' not in frames[frame_idx] or 
                        len(frames[frame_idx]['bodyparts']) <= animal_idx or 
                        len(frames[frame_idx]['bodyparts'][animal_idx]) <= bp_idx):
                        continue
                        
                    # Calculate interpolated positions
                    if method == "linear":
                        # Linear interpolation
                        total_frames = after_frame - before_frame
                        progress = (frame_idx - before_frame) / total_frames
                        
                        x = before_x + progress * (after_x - before_x)
                        y = before_y + progress * (after_y - before_y)
                    else:
                        # Nearest neighbor or fallback
                        if frame_idx - before_frame <= after_frame - frame_idx:
                            x, y = before_x, before_y
                        else:
                            x, y = after_x, after_y
                    
                    # Update the data with interpolated value
                    frames[frame_idx]['bodyparts'][animal_idx][bp_idx] = [x, y, interp_confidence]
                    
                    # Mark that we fixed something in this frame-level discontinuity
                    frame_fixed = True
            
            # Count as fixed only if at least one bodypart was fixed
            if frame_fixed:
                fixed_discontinuities += 1
        else:
            # Regular bodypart-level discontinuity handling (existing code)
            # Get positions before and after the gap
            before_x, before_y = None, None
            after_x, after_y = None, None
            
            # Look for valid data point before gap
            while before_frame >= 0:
                if ('bodyparts' in frames[before_frame] and 
                    len(frames[before_frame]['bodyparts']) > animal_idx and
                    len(frames[before_frame]['bodyparts'][animal_idx]) > bodypart_idx):
                    
                    x, y, conf = frames[before_frame]['bodyparts'][animal_idx][bodypart_idx]
                    if not (np.isnan(x) or np.isnan(y) or conf == -1):
                        before_x, before_y = x, y
                        break
                before_frame -= 1
            
            # Look for valid data point after gap
            while after_frame < len(frames):
                if ('bodyparts' in frames[after_frame] and 
                    len(frames[after_frame]['bodyparts']) > animal_idx and
                    len(frames[after_frame]['bodyparts'][animal_idx]) > bodypart_idx):
                    
                    x, y, conf = frames[after_frame]['bodyparts'][animal_idx][bodypart_idx]
                    if not (np.isnan(x) or np.isnan(y) or conf == -1):
                        after_x, after_y = x, y
                        break
                after_frame += 1
            
            # Skip if we still don't have valid points before or after
            if before_x is None or after_x is None:
                continue

            # Interpolate based on the chosen method
            points_fixed = False  # Track if we actually fixed any points
            for frame_idx in range(start_frame, end_frame + 1):
                if ('bodyparts' not in frames[frame_idx] or 
                    len(frames[frame_idx]['bodyparts']) <= animal_idx or 
                    len(frames[frame_idx]['bodyparts'][animal_idx]) <= bodypart_idx):
                    continue
                    
                # Get the current data point
                curr_x, curr_y, curr_conf = frames[frame_idx]['bodyparts'][animal_idx][bodypart_idx]
                
                # Only interpolate if original data is invalid (NaN or low confidence)
                if np.isnan(curr_x) or np.isnan(curr_y) or curr_conf < 0.5:
                    # Calculate interpolated positions
                    if method == "linear":
                        # Linear interpolation
                        total_frames = after_frame - before_frame
                        progress = (frame_idx - before_frame) / total_frames
                        
                        x = before_x + progress * (after_x - before_x)
                        y = before_y + progress * (after_y - before_y)
                    else:
                        # Nearest neighbor or fallback
                        if frame_idx - before_frame <= after_frame - frame_idx:
                            x, y = before_x, before_y
                        else:
                            x, y = after_x, after_y
                    
                    # Update the data with interpolated value
                    # Use a confidence value that's distinguishable as interpolated (e.g., 0.51)
                    frames[frame_idx]['bodyparts'][animal_idx][bodypart_idx] = [x, y, interp_confidence]
                    points_fixed = True
                # Otherwise keep the original data (no interpolation needed)

            # Count as fixed only if at least one point was actually fixed
            if points_fixed:
                fixed_discontinuities += 1
            
    return processed_data, fixed_discontinuities, max_gap_found


def extract_trajectory(data, animal_idx, bodypart_idx):
    """Extract trajectory data for a specific animal and bodypart."""
    x_values = []
    y_values = []
    frame_indices = []
    
    # Extract actual data from data wrapper if needed
    if isinstance(data, dict) and 'data' in data:
        frames = data['data']
    else:
        frames = data
    
    # Iterate through frames and extract coordinates
    for frame_idx, frame in enumerate(frames):
        if 'bodyparts' in frame and len(frame['bodyparts']) > animal_idx:
            animal_data = frame['bodyparts'][animal_idx]
            if len(animal_data) > bodypart_idx:
                x, y, _ = animal_data[bodypart_idx]
                x_values.append(x)
                y_values.append(y)
                frame_indices.append(frame_idx)
    
    return x_values, y_values, frame_indices


def count_fixed_points(original_data, processed_data):
    """Count how many data points were fixed by comparing original and processed data."""
    fixed_count = 0
    
    # Get the metadata to see if we stored the interpolation confidence
    interp_confidence = 0.51  # Default value to look for
    if isinstance(processed_data, dict) and 'metadata' in processed_data:
        interp_confidence = processed_data['metadata'].get('interp_confidence', 0.51)
    
    # Extract actual data from data wrappers if needed
    if isinstance(original_data, dict) and 'data' in original_data:
        original_frames = original_data['data']
    else:
        original_frames = original_data
        
    if isinstance(processed_data, dict) and 'data' in processed_data:
        processed_frames = processed_data['data']
    else:
        processed_frames = processed_data
    
    # Iterate through all frames and compare
    for frame_idx in range(min(len(original_frames), len(processed_frames))):
        orig_frame = original_frames[frame_idx]
        proc_frame = processed_frames[frame_idx]
        
        if 'bodyparts' not in orig_frame or 'bodyparts' not in proc_frame:
            continue
            
        for animal_idx in range(min(len(orig_frame['bodyparts']), len(proc_frame['bodyparts']))):
            orig_animal = orig_frame['bodyparts'][animal_idx]
            proc_animal = proc_frame['bodyparts'][animal_idx]
            
            for bp_idx in range(min(len(orig_animal), len(proc_animal))):
                orig_x, orig_y, orig_conf = orig_animal[bp_idx]
                proc_x, proc_y, proc_conf = proc_animal[bp_idx]
                
                # Check if point was fixed (values changed and confidence matches interpolation value)
                if (abs(proc_conf - interp_confidence) < 1e-6 and 
                    (np.isnan(orig_x) or np.isnan(orig_y) or 
                    abs(orig_x - proc_x) > 1e-6 or 
                    abs(orig_y - proc_y) > 1e-6)):
                    fixed_count += 1
    
    return fixed_count

def extract_fixed_points(original_data, processed_data, animal_idx, bodypart_idx, interp_confidence=0.51):
    """
    Extract only the interpolated/fixed points for visualization.
    
    Parameters:
    -----------
    interp_confidence : float
        The confidence value assigned to interpolated points (default: 0.51)
    """
    x_values = []
    y_values = []
    frame_indices = []
    
    # Extract actual data from data wrappers if needed
    if isinstance(original_data, dict) and 'data' in original_data:
        original_frames = original_data['data']
    else:
        original_frames = original_data
        
    if isinstance(processed_data, dict) and 'data' in processed_data:
        processed_frames = processed_data['data']
        # Get custom confidence value from metadata if available
        if 'metadata' in processed_data and 'interp_confidence' in processed_data['metadata']:
            interp_confidence = processed_data['metadata']['interp_confidence']
    else:
        processed_frames = processed_data
    
    # Iterate through frames and extract all fixed/interpolated points
    for frame_idx in range(min(len(original_frames), len(processed_frames))):
        if ('bodyparts' in processed_frames[frame_idx] and 
            len(processed_frames[frame_idx]['bodyparts']) > animal_idx):
            
            proc_animal = processed_frames[frame_idx]['bodyparts'][animal_idx]
            
            if (len(proc_animal) > bodypart_idx and 
                'bodyparts' in original_frames[frame_idx] and 
                len(original_frames[frame_idx]['bodyparts']) > animal_idx and 
                len(original_frames[frame_idx]['bodyparts'][animal_idx]) > bodypart_idx):
                
                # Get original and processed data
                orig_x, orig_y, orig_conf = original_frames[frame_idx]['bodyparts'][animal_idx][bodypart_idx]
                proc_x, proc_y, proc_conf = proc_animal[bodypart_idx]
                
                # Check if point was interpolated or fixed
                orig_is_missing = np.isnan(orig_x) or np.isnan(orig_y) or orig_conf < 0.5
                values_changed = False
                
                # If original value existed, check if values changed
                if not orig_is_missing:
                    values_changed = (abs(orig_x - proc_x) > 1e-6 or abs(orig_y - proc_y) > 1e-6)
                
                # Include point if:
                # 1. It was interpolated (missing in original but present in processed)
                # 2. OR if it has the specific interpolated confidence value
                # 3. OR if it significantly differs from the original value
                if ((orig_is_missing and not (np.isnan(proc_x) or np.isnan(proc_y))) or 
                    abs(proc_conf - interp_confidence) < 1e-6 or 
                    values_changed):
                    x_values.append(proc_x)
                    y_values.append(proc_y)
                    frame_indices.append(frame_idx)
    
    return x_values, y_values, frame_indices
