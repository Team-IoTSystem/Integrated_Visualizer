from flask import Flask, render_template, Markup
from DistanceVisualizer.heatmap import main
app = Flask(__name__)


@app.route('/heatmap')
def show_heatmap():
    d3map = Markup(main())
    return render_template('TEST/dashboard.html', heatmap=d3map)

if __name__ == '__main__':
    app.run()
