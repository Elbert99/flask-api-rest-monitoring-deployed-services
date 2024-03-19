from flask import Flask
from service_monitor import ServiceMonitor

app = Flask(__name__)


@app.cli.command("run-index")
@app.route('/')
def index():
    monitor = ServiceMonitor()
    monitor.start_monitoring()


if __name__ == 'main':
    app.run(debug=True)
