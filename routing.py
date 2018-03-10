from flask import Flask, render_template, Markup
from DistanceVisualizer.heatmap import main
app = Flask(__name__)

jinja_options = app.jinja_options.copy()

jinja_options.update(dict(
    block_start_string='<%',
    block_end_string='%>',
    variable_start_string='%%',
    variable_end_string='%%',
    comment_start_string='<#',
    comment_end_string='#>'
))
app.jinja_options = jinja_options

@app.route('/')
def show_dashboard():
    d3map = main()
    if d3map is None:
        d3map = 'Heatmap is unavailable.'
    return render_template('index.html', heatmap=Markup(d3map))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
