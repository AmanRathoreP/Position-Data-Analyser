# Author: Aman Rathore

import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.stats import gaussian_kde

def create_time_series_plot(df, columns, title="", plot_type=None, fps=30):
    """Create a time series plot with proper time units based on FPS."""
    # Determine best time unit to use based on total duration
    if 'seconds' in df.columns:
        max_seconds = df['seconds'].max()
        
        if max_seconds < 120:  # Less than 2 minutes, use seconds
            time_col = 'seconds'
            time_label = 'Time (seconds)'
        else:  # Use minutes for longer recordings
            time_col = 'minutes'
            time_label = 'Time (minutes)'
    else:
        # Fallback to frames if time not calculated
        time_col = 'frame'
        time_label = 'Frame'
    
    # Create the plot
    fig = px.line(
        df, 
        x=time_col, 
        y=columns, 
        title=title
    )
    
    # Update axis labels
    fig.update_xaxes(title_text=time_label)
    
    return fig

def create_heatmap(xs, ys, grid_size=100, title=None, fps=30):
    """Create an occupancy heatmap using Gaussian KDE with support for time information."""
    # Drop any NaNs
    mask = ~(np.isnan(xs) | np.isnan(ys))
    xs_clean = xs[mask]
    ys_clean = ys[mask]
    
    if len(xs_clean) < 2:  # Not enough data for KDE
        fig = go.Figure()
        fig.update_layout(
            title="Not enough valid data points for heatmap",
            template="plotly_white"
        )
        return fig
    
    coords = np.vstack([xs_clean, ys_clean])
    
    # Calculate the KDE
    kde = gaussian_kde(coords)
    
    # Create grid for heatmap
    x_min, y_min = coords.min(axis=1)
    x_max, y_max = coords.max(axis=1)
    
    # Add margin to min/max
    margin = 0.05 * max(x_max - x_min, y_max - y_min)
    x_min -= margin
    x_max += margin
    y_min -= margin
    y_max += margin
    
    xi = np.linspace(x_min, x_max, grid_size)
    yi = np.linspace(y_min, y_max, grid_size)
    xx, yy = np.meshgrid(xi, yi)
    grid_coords = np.vstack([xx.ravel(), yy.ravel()])
    zi = kde(grid_coords).reshape(xx.shape)
    
    # Create the heatmap
    fig = go.Figure(go.Heatmap(
        z=zi,
        x=xi,
        y=yi,
        colorscale="Viridis",
        colorbar=dict(title="Density")
    ))
    
    # Add time information to the title if needed
    duration_sec = len(xs) / fps if fps > 0 else 0
    if duration_sec >= 60:
        duration_str = f"{duration_sec/60:.1f} minutes"
    else:
        duration_str = f"{duration_sec:.1f} seconds"
    
    display_title = title or "Occupancy Heatmap"
    display_title = f"{display_title} (Duration: {duration_str})"
    
    fig.update_layout(
        title=display_title,
        xaxis_title="X coordinate",
        yaxis_title="Y coordinate",
        template="plotly_white"
    )
    
    return fig

def create_trajectory_plot(df, title=None, fps=30):
    """Create a trajectory plot using the x and y position data with time information."""
    if df.empty or df["x"].isna().all() or df["y"].isna().all():
        fig = go.Figure()
        fig.update_layout(
            title="Not enough valid data points for trajectory",
            template="plotly_white"
        )
        return fig
    
    # Determine best time column to use for coloring
    if 'seconds' in df.columns:
        max_seconds = df['seconds'].max()
        
        if max_seconds < 120:  # Less than 2 minutes, use seconds
            time_col = 'seconds'
            time_label = 'Time (seconds)'
        else:  # Use minutes for longer recordings
            time_col = 'minutes'
            time_label = 'Time (minutes)'
    else:
        # Fallback to frames if time not calculated
        time_col = 'frame'
        time_label = 'Frame'
    
    # Create a colorscale based on time for temporal information
    fig = px.scatter(df, x="x", y="y", color=time_col,
                     color_continuous_scale="Viridis",
                     title=title or "Movement Trajectory",
                     labels={time_col: time_label})
    
    # Add lines connecting the points
    fig.add_trace(go.Scatter(
        x=df["x"], 
        y=df["y"],
        mode="lines",
        line=dict(color="rgba(255,255,255,0.5)", width=1),
        showlegend=False
    ))
    
    fig.update_layout(
        xaxis_title="X coordinate",
        yaxis_title="Y coordinate",
        template="plotly_white",
        coloraxis_colorbar=dict(title=time_label)
    )
    
    return fig

def create_distribution_plot(df, column, title=None):
    """Create a distribution plot for the given data column."""
    fig = px.histogram(df, x=column, histnorm="probability density",
                       title=title or f"Distribution of {column.capitalize()}")
    fig.update_layout(
        xaxis_title=column.capitalize(),
        yaxis_title="Probability Density",
        template="plotly_white"
    )
    
    # Add KDE curve if enough data
    if len(df) > 5 and not df[column].isna().all():
        # Calculate KDE
        kde_x = np.linspace(df[column].min(), df[column].max(), 1000)
        kde = gaussian_kde(df[column].dropna())
        kde_y = kde(kde_x)
        
        # Add KDE curve
        fig.add_trace(go.Scatter(
            x=kde_x,
            y=kde_y,
            mode="lines",
            line=dict(color="red", width=2),
            name="KDE"
        ))
    
    return fig