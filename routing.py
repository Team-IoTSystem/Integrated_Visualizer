from flask import Flask, render_template, Markup
import DistanceVisualizer.heatmap as heatmap

app = Flask(__name__)


@app.route('/heatmap')
def hello():
    d3map = Markup(heatmap.main(("24:0A:C4:11:9A:30", "30:AE:A4:03:8A:44",)))
    return render_template('TEST/dashboard.html', heatmap=d3map)

if __name__ == '__main__':
    app.run()
