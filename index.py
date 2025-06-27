# Author: Aman Rathore

from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from app import app
from layouts.main_layout import create_layout
from callbacks.import_callbacks import register_import_callbacks
from callbacks.discontinuity_callbacks import register_discontinuity_callbacks
from callbacks.filter_callbacks import register_filter_callbacks
from callbacks.plot_callbacks import register_plot_callbacks

# Create main layout
app.layout = create_layout()

# Register callbacks
register_import_callbacks(app)
register_discontinuity_callbacks(app)
register_filter_callbacks(app)
register_plot_callbacks(app)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)