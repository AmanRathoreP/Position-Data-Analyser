from dash.dependencies import Input, Output, State
from dash import html

from utils.data_processing import parse_uploaded_json, get_data_summary

def register_import_callbacks(app):
    """Register callbacks for the data import step."""
    
    @app.callback(
        [
            Output("file-info", "children"),
            Output("json-preview", "children"),
            Output("stored-raw-data", "data"),
            Output("proceed-to-filter-btn", "disabled")
        ],
        [Input("upload-data", "contents")],
        [State("upload-data", "filename")]
    )
    def update_import_output(contents, filename):
        """Update the output based on the uploaded file."""
        if contents is None:
            return (
                html.P("No file selected"),
                "No file selected",
                None,
                True
            )
        
        # Parse uploaded JSON
        data, error = parse_uploaded_json(contents)
        
        if error or not data:
            return (
                html.Div([
                    html.P(f"Error parsing file: {error}", style={"color": "red"}),
                ]),
                html.P(f"Error: {error}", style={"color": "red"}),
                None,
                True
            )
        
        # Get summary info
        summary = get_data_summary(data)
        
        # Create file info display
        file_info = html.Div([
            html.P(f"File: {filename}", className="mb-1"),
            html.P(f"Frames: {summary.get('num_frames', 'Unknown')}", className="mb-1"),
            html.P(f"Animals: {summary.get('num_animals', 'Unknown')}", className="mb-1"),
            html.P(f"Body Parts: {len(summary.get('bodyparts', []))}", className="mb-1"),
        ])
        
        # Create JSON preview
        preview = html.Pre(
            str(data[0] if data else {}),
            style={
                "maxHeight": "200px", 
                "overflow": "auto",
                "whiteSpace": "pre-wrap",
                "fontSize": "0.8rem"
            }
        )
        
        return file_info, preview, data, False
    
    @app.callback(
        Output("workflow-tabs", "active_tab"),
        [Input("proceed-to-filter-btn", "n_clicks")],
        [State("stored-raw-data", "data")]
    )
    def proceed_to_filter(n_clicks, data):
        """Proceed to the filter tab when the button is clicked."""
        if n_clicks is None or not data:
            return "tab-import"
        
        return "tab-filter"