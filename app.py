"""
Main app entry point that launches all three Flask applications.
"""

import subprocess
import sys
import os
import signal
import time
import threading
import webbrowser
from flask import Flask, render_template, jsonify, redirect
import requests
import config

# Initialize the main Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Store the process objects for cleanup
app_processes = []

def launch_app(app_path, port):
    """Launch a Flask app as a separate process."""
    process = subprocess.Popen([sys.executable, app_path])
    app_processes.append(process)
    print(f"Launched app {app_path} on port {port}")
    return process

def wait_for_app(url, max_retries=10):
    """Wait for an app to be ready by checking its URL."""
    for i in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"App at {url} is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    print(f"App at {url} did not start properly")
    return False

@app.route('/')
def index():
    """Main app index showing links to all sub-apps."""
    return render_template('index.html', 
                          kinesthetic_url=f"http://localhost:{config.KINESTHETIC_APP_PORT}",
                          readwrite_url=f"http://localhost:{config.READWRITE_APP_PORT}",
                          visual_url=f"http://localhost:{config.VISUAL_APP_PORT}")  # Added visual URL

@app.route('/kinesthetic')
def kinesthetic_redirect():
    """Redirect to the kinesthetic app."""
    return redirect(f"http://localhost:{config.KINESTHETIC_APP_PORT}")

@app.route('/readwrite')
def readwrite_redirect():
    """Redirect to the readwrite app."""
    return redirect(f"http://localhost:{config.READWRITE_APP_PORT}")

@app.route('/visual')
def visual_redirect():
    """Redirect to the visual app."""
    return redirect(f"http://localhost:{config.VISUAL_APP_PORT}")

@app.route('/api/status')
def api_status():
    """API endpoint to check the status of all apps."""
    status = {
        'main': 'running',
        'kinesthetic': 'unknown',
        'readwrite': 'unknown',
        'visual': 'unknown'  # Added visual status
    }
    
    # Check kinesthetic app
    try:
        response = requests.get(f"http://localhost:{config.KINESTHETIC_APP_PORT}/api/info")
        if response.status_code == 200:
            status['kinesthetic'] = 'running'
    except:
        status['kinesthetic'] = 'not running'
    
    # Check readwrite app
    try:
        response = requests.get(f"http://localhost:{config.READWRITE_APP_PORT}/api/info")
        if response.status_code == 200:
            status['readwrite'] = 'running'
    except:
        status['readwrite'] = 'not running'
    
    # Check visual app
    try:
        response = requests.get(f"http://localhost:{config.VISUAL_APP_PORT}/api/info")
        if response.status_code == 200:
            status['visual'] = 'running'
    except:
        status['visual'] = 'not running'
    
    return jsonify(status)

def create_templates_folder():
    """Create templates folder if it doesn't exist."""
    os.makedirs('templates', exist_ok=True)

def create_main_template():
    """Create the main app's index.html template."""
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Learning Apps Hub</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        .app-link {
            display: inline-block;
            margin: 10px;
            padding: 15px 25px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        .app-link:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Learning Apps Hub</h1>
        <p>Welcome to the central hub for educational applications.</p>
        
        <h2>Available Applications</h2>
        <div>
            <a class="app-link" href="{{ kinesthetic_url }}">Kinesthetic Learning App</a>
            <a class="app-link" href="{{ readwrite_url }}">Read/Write Learning App</a>
            <a class="app-link" href="{{ visual_url }}">Visual Learning App</a>
        </div>
        
        <h2>System Status</h2>
        <div id="status">Checking system status...</div>
    </div>

    <script>
        // Fetch and display app status
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    let statusHtml = '<ul>';
                    for (const [app, status] of Object.entries(data)) {
                        statusHtml += `<li>${app}: <span style="color: ${status === 'running' ? 'green' : 'red'}">${status}</span></li>`;
                    }
                    statusHtml += '</ul>';
                    document.getElementById('status').innerHTML = statusHtml;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 'Error checking system status';
                });
        }
        
        // Check status on page load and every 10 seconds
        updateStatus();
        setInterval(updateStatus, 10000);
    </script>
</body>
</html>""")

def cleanup():
    """Clean up all processes on exit."""
    for process in app_processes:
        try:
            process.terminate()
            print(f"Terminated process {process.pid}")
        except:
            pass

def open_browser():
    """Open browser to the main app after a short delay."""
    time.sleep(2)
    webbrowser.open(f"http://localhost:{config.MAIN_APP_PORT}")

if __name__ == '__main__':
    # Create necessary templates
    create_templates_folder()
    create_main_template()
    
    # Register cleanup function
    import atexit
    atexit.register(cleanup)
    
    # Launch the other apps
    kinesthetic_process = launch_app('kinesthetic/app.py', config.KINESTHETIC_APP_PORT)
    readwrite_process = launch_app('readwrite/app.py', config.READWRITE_APP_PORT)
    visual_process = launch_app('visual/app.py', config.VISUAL_APP_PORT)  # Launch visual app
    
    # Wait for the apps to be ready
    kinesthetic_url = f"http://localhost:{config.KINESTHETIC_APP_PORT}"
    readwrite_url = f"http://localhost:{config.READWRITE_APP_PORT}"
    visual_url = f"http://localhost:{config.VISUAL_APP_PORT}"  # Add visual URL
    
    # Start a thread to open the browser when the apps are ready
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the main app
    app.run(debug=True, port=config.MAIN_APP_PORT, use_reloader=False)
