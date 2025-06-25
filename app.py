# Author: Aman Rathore
# Contact: amanr.me | amanrathore9753 <at> gmail <dot> com
# Created on: Wednesday, June 25, 2025 at 21:35

from dash import Dash, html

app = Dash()

app.layout = [html.Div(children='Position Data Analyser')]

if __name__ == '__main__':
    app.run(debug=True)
