# Author: Aman Rathore

import dash
import traceback
from dash import Input, Output, State, callback, no_update
import plotly.graph_objects as go
from utils.zones_handling import ZonesHandler
import base64
from PIL import Image
import io

def register_zone_callbacks(app):
    @app.callback(
        Output("zones-plot", "figure"),
        Output("zones-error", "children"),
        Output("zones-error", "is_open"),
        Output("zones-data-store", "data"),
        Input("update-zones-btn", "n_clicks"),
        State("zone-definition-input", "value"),
        State("background-image-store", "data"),
        State("image-opacity-slider", "value"),
        prevent_initial_call=True
    )
    def update_zones(n_clicks, zone_code, background_image, opacity):
        """Update the zones plot based on the provided zone definition code."""
        if not n_clicks:
            return {}, "", False, None
        
        try:
            # Create a ZonesHandler object from the code
            zh = ZonesHandler(zone_code, circle_resolution=128)
            zones = zh.get_zones()
            
            if not zones:
                return {}, "No zones defined in the code", True, None
            
            # Create figure
            fig = go.Figure()
            
            # Calculate bounds for all zones
            bounds = [zh.get_bounds(z) for z in zones]
            xmin, ymin = min(b[0] for b in bounds), min(b[1] for b in bounds)
            xmax, ymax = max(b[2] for b in bounds), max(b[3] for b in bounds)
            
            # Add some padding to the bounds
            padding = max(xmax - xmin, ymax - ymin) * 0.05
            xmin -= padding
            xmax += padding
            ymin -= padding
            ymax += padding
            
            # Add background image if available - position to match exact plot dimensions
            if background_image:
                img_width, img_height = get_image_size_from_base64(background_image)
                plot_xmin, plot_xmax = 0, img_width
                plot_ymin, plot_ymax = 0, img_height

                fig.add_layout_image(
                    dict(
                        source=background_image,
                        xref="x",
                        yref="y",
                        x=0,
                        y=img_height,  # top-left
                        sizex=img_width,
                        sizey=-img_height,  # negative to flip y-axis
                        sizing="stretch",
                        opacity=opacity,
                        layer="below"
                    )
                )
            else:
                # fallback to zone bounds if no image
                plot_xmin, plot_xmax = xmin, xmax
                plot_ymin, plot_ymax = ymin, ymax
            
            # Store trace indices per zone for the buttons
            traces_per_zone = {}
            
            # Add zones to the plot
            for i, name in enumerate(zones):
                start = len(fig.data)
                add_zone_traces(fig, zh.zones[name], visible=(i==0), name=name)
                traces_per_zone[name] = list(range(start, len(fig.data)))
            
            # Create annotation function
            def make_annotation(z):
                area = zh.get_area(z)
                per = zh.get_perimeter(z)
                return dict(
                    text=f"Area: {area:.2f} | Perimeter: {per:.2f}",
                    xref="paper", yref="paper",
                    x=0.02, y=0.98,
                    showarrow=False,
                    font=dict(size=12)
                )
            
            # Create dropdown buttons for zone selection
            buttons = []
            for name in zones:
                # Create visibility mask
                vis = [False] * len(fig.data)
                for tidx in traces_per_zone[name]:
                    vis[tidx] = True
                
                buttons.append(dict(
                    label=name,
                    method="update",
                    args=[
                        {"visible": vis},
                        {
                            "title": {"text": f"Zone: {name}"},
                            "annotations": [make_annotation(name)]
                        }
                    ]
                ))
            
            # Update layout with fixed aspect ratio and the calculated bounds
            fig.update_layout(
                title_text=f"Zone: {zones[0]}",
                annotations=[make_annotation(zones[0])],
                updatemenus=[dict(
                    active=0,
                    buttons=buttons,
                    x=1.1, y=1, xanchor="left", yanchor="top"
                )],
                xaxis=dict(title="X", range=[plot_xmin, plot_xmax]),
                yaxis=dict(title="Y", range=[plot_ymin, plot_ymax], scaleanchor="x", scaleratio=1),
                showlegend=False,
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # Store the ZonesHandler data
            zones_data = {
                "code": zone_code,
                "zones": zones
            }
            
            return fig, "", False, zones_data
            
        except Exception as e:
            error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
            return {}, error_msg, True, None

    @app.callback(
        Output("background-image-store", "data"),
        Output("uploaded-image-name", "children"),
        Input("upload-background-image", "contents"),
        State("upload-background-image", "filename"),
        prevent_initial_call=True
    )
    def store_background_image(contents, filename):
        """Store the uploaded background image."""
        if not contents:
            return None, ""
        
        # The content string starts with "data:image/png;base64," or similar
        return contents, f"Uploaded: {filename}"
    
    @app.callback(
        Output("zone-definition-input", "value"),
        Input("clear-zones-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def clear_zone_definition(n_clicks):
        """Clear the zone definition text area."""
        if n_clicks:
            return ""
        return no_update
    
    @app.callback(
        Output("workflow-tabs", "active_tab", allow_duplicate=True),
        [Input("proceed-to-filter-btn-zones", "n_clicks")],
        [State("stored-processed-data", "data")],
        prevent_initial_call=True
    )
    def proceed_to_filtering(n_clicks, processed_data):
        """Proceed to the filter tab when the button is clicked."""
        if n_clicks is None or not processed_data:
            raise dash.exceptions.PreventUpdate
        return "tab-filter"



def add_zone_traces(fig, geom, visible=False, name=None):
    """Helper to add all traces for a given zone geometry."""
    parts = getattr(geom, "geoms", [geom])
    for part in parts:
        if part.geom_type != "Polygon":
            continue
        # exterior ring
        x_ext, y_ext = part.exterior.xy
        fig.add_trace(go.Scatter(
            x=list(x_ext), y=list(y_ext),
            fill="toself",
            name=name,
            visible=visible,
            hoverinfo="name",
            line=dict(width=2),
            fillcolor="rgba(0, 0, 255, 0.4)",  # zone opacity
        ))
        # interior rings (holes)
        for interior in part.interiors:
            xi, yi = interior.xy
            fig.add_trace(go.Scatter(
                x=list(xi), y=list(yi),
                fill="toself",
                fillcolor="rgba(255, 255, 255, 0.1)",  # zone opacity
                line=dict(width=0),
                hoverinfo="none",
                showlegend=False,
                visible=visible
            ))


def get_image_size_from_base64(base64_str):
    """Extract width and height from a base64 image string."""
    header, encoded = base64_str.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(img_bytes))
    return img.width, img.height