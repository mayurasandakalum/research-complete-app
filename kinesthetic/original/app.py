"""
Kinesthetic app - can run independently or as part of the main app.
"""

from flask import Flask, render_template, jsonify
import sys
import os

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

@app.route('/')
def index():
    return render_template('index.html', title='Kinesthetic App')

@app.route('/api/info')
def api_info():
    return jsonify({
        'app': 'Kinesthetic App',
        'status': 'running'
    })

if __name__ == '__main__':
    # If run directly, use the port from config
    app.run(debug=True, port=config.KINESTHETIC_APP_PORT)
