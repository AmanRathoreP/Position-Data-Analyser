# Author: Aman Rathore

import json
import base64
import pandas as pd
import numpy as np
from io import StringIO

def parse_uploaded_json(contents):
    """Parse uploaded JSON file contents and return the data."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string).decode('utf-8')
    
    try:
        data = json.loads(decoded)
        return data, None
    except Exception as e:
        return None, str(e)

def get_data_summary(data):
    """Get summary information about the tracking data."""
    summary = {}
    
    # Handle different data structures
    if isinstance(data, dict) and 'data' in data:
        # New format with metadata
        actual_data = data['data']
    else:
        # Old format without metadata wrapper
        actual_data = data
    
    # Empty or invalid data check
    if not actual_data or not isinstance(actual_data, list) or len(actual_data) == 0:
        return {
            'num_frames': 0,
            'num_animals': 0,
            'bodyparts': []
        }
    
    # Get number of frames
    summary['num_frames'] = len(actual_data)
    
    # Get number of animals
    num_animals = 0
    if 'bbox_scores' in actual_data[0]:
        num_animals = len(actual_data[0]['bbox_scores'])
    elif 'bodyparts' in actual_data[0]:
        num_animals = len(actual_data[0]['bodyparts'])
    summary['num_animals'] = num_animals
    
    # Get body parts (assume consistent across frames and animals)
    bodyparts = []
    if num_animals > 0 and 'bodyparts' in actual_data[0] and len(actual_data[0]['bodyparts']) > 0:
        # Number of bodyparts is the length of the first animal's bodyparts array
        num_bodyparts = len(actual_data[0]['bodyparts'][0])
        bodyparts = list(range(num_bodyparts))
    summary['bodyparts'] = bodyparts
    
    return summary

def filter_data(raw_data, num_animals=2, confidence_threshold=0.5, selected_bodyparts=None):
    """Filter the tracking data based on user parameters."""
    filtered_data = []
    
    # Filter frames and apply thresholds
    for frame in raw_data:
        frame_copy = frame.copy()
        
        # Limit number of animals
        if 'bboxes' in frame_copy:
            frame_copy['bboxes'] = frame_copy['bboxes'][:num_animals]
        if 'bbox_scores' in frame_copy:
            frame_copy['bbox_scores'] = frame_copy['bbox_scores'][:num_animals]
        if 'bodyparts' in frame_copy:
            frame_copy['bodyparts'] = frame_copy['bodyparts'][:num_animals]
            
            # Apply confidence threshold
            for animal_idx, animal_data in enumerate(frame_copy['bodyparts']):
                for bp_idx, (x, y, conf) in enumerate(animal_data):
                    # If confidence below threshold or not in selected bodyparts, set to NaN
                    if (conf < confidence_threshold) or (
                        selected_bodyparts and bp_idx not in selected_bodyparts
                    ):
                        frame_copy['bodyparts'][animal_idx][bp_idx] = [np.nan, np.nan, np.nan]
        
        filtered_data.append(frame_copy)
    
    # Return data with metadata structure
    return {
        'data': filtered_data,
        'metadata': {}  # Will be filled by callback
    }

def extract_time_series(filtered_data, animal_idx, bodypart_idx):
    """Extract time series data for a specific animal and body part."""
    # Handle different data storage formats
    if isinstance(filtered_data, dict) and 'data' in filtered_data:
        data = filtered_data['data']
        metadata = filtered_data.get('metadata', {})
    else:
        data = filtered_data
        metadata = {}
    
    # Get FPS value from metadata or use default
    fps = metadata.get('fps', 30)  # Default to 30 fps if not specified
    
    frames = []
    x_values = []
    y_values = []
    
    for frame_idx, frame in enumerate(data):
        if 'bodyparts' in frame and len(frame['bodyparts']) > animal_idx:
            animal_data = frame['bodyparts'][animal_idx]
            if len(animal_data) > bodypart_idx:
                x, y, conf = animal_data[bodypart_idx]
                frames.append(frame_idx)
                x_values.append(x)
                y_values.append(y)
    
    # Create a DataFrame
    df = pd.DataFrame({
        'frame': frames,
        'x': x_values,
        'y': y_values
    })
    
    # Add time columns based on FPS
    df['seconds'] = df['frame'] / fps
    df['minutes'] = df['seconds'] / 60
    
    return df, fps

def create_occupancy_data(data, animal_idx, bodypart_idx, grid_size=100):
    """Create occupancy heatmap data for a specific animal and bodypart."""
    xs, ys = [], []
    
    for frame in data:
        if 'bodyparts' in frame and len(frame['bodyparts']) > animal_idx:
            bodyparts = frame['bodyparts'][animal_idx]
            if len(bodyparts) > bodypart_idx:
                x, y, conf = bodyparts[bodypart_idx]
                if not np.isnan(x) and not np.isnan(y):
                    xs.append(x)
                    ys.append(y)
    
    return np.array(xs), np.array(ys)

def data_to_csv(data, animal_idx, bodypart_idx):
    """Convert tracking data to CSV for export."""
    df = extract_time_series(data, animal_idx, bodypart_idx)
    return df.to_csv(index=False)

def add_metadata_to_list(data_list):
    """Adds metadata to a list or converts to a dict with data and metadata."""
    # Convert to dict structure with data and metadata
    result = {
        'data': data_list,
        'metadata': {}
    }
    
    return result