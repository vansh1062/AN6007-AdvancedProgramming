import logging
import json
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from flask import Flask, request, g
import threading
from typing import Dict, Any
import sys

class MeterLoggingSystem:
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = log_directory
        self.setup_log_directory()
        self.setup_loggers()
        self.lock = threading.Lock()

    def setup_log_directory(self):
        """Create necessary log directories if they don't exist"""
        directories = [
            self.log_directory,
            f"{self.log_directory}/requests",
            f"{self.log_directory}/meter_readings",
            f"{self.log_directory}/errors",
            f"{self.log_directory}/system"
        ]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        # Request Logger
        self.request_logger = logging.getLogger('request_logger')
        self.request_logger.setLevel(logging.INFO)
        request_handler = TimedRotatingFileHandler(
            f"{self.log_directory}/requests/requests.log",
            when="midnight",
            interval=1,
            backupCount=30
        )
        request_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.request_logger.addHandler(request_handler)

        # Meter Reading Logger
        self.meter_logger = logging.getLogger('meter_logger')
        self.meter_logger.setLevel(logging.INFO)
        meter_handler = RotatingFileHandler(
            f"{self.log_directory}/meter_readings/readings.log",
            maxBytes=10000000,  # 10MB
            backupCount=10
        )
        meter_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.meter_logger.addHandler(meter_handler)

        # Error Logger
        self.error_logger = logging.getLogger('error_logger')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = RotatingFileHandler(
            f"{self.log_directory}/errors/errors.log",
            maxBytes=10000000,  # 10MB
            backupCount=10
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n%(message)s\n'
        ))
        self.error_logger.addHandler(error_handler)

        # System Logger
        self.system_logger = logging.getLogger('system_logger')
        self.system_logger.setLevel(logging.INFO)
        system_handler = TimedRotatingFileHandler(
            f"{self.log_directory}/system/system.log",
            when="midnight",
            interval=1,
            backupCount=30
        )
        system_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.system_logger.addHandler(system_handler)

    def log_request(self, request_data: Dict[str, Any]):
        """Log incoming API requests"""
        with self.lock:
            self.request_logger.info(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'method': request_data.get('method'),
                'path': request_data.get('path'),
                'headers': dict(request_data.get('headers', {})),
                'body': request_data.get('body'),
                'ip': request_data.get('ip')
            }))

    def log_meter_reading(self, meter_data: Dict[str, Any]):
        """Log meter readings"""
        with self.lock:
            self.meter_logger.info(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'meter_id': meter_data.get('meter_id'),
                'reading': meter_data.get('reading'),
                'status': meter_data.get('status')
            }))

    def log_error(self, error_data: Dict[str, Any]):
        """Log errors"""
        with self.lock:
            self.error_logger.error(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'error_type': error_data.get('type'),
                'message': error_data.get('message'),
                'stack_trace': error_data.get('stack_trace')
            }))

    def log_system_event(self, event_data: Dict[str, Any]):
        """Log system events"""
        with self.lock:
            self.system_logger.info(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'event_type': event_data.get('type'),
                'message': event_data.get('message'),
                'details': event_data.get('details')
            }))

class RequestLoggerMiddleware:
    def __init__(self, app: Flask, logger: MeterLoggingSystem):
        self.app = app
        self.logger = logger

    def __call__(self, environ, start_response):
        """WSGI middleware to log all requests"""
        request = Request(environ)
        
        # Log request before processing
        self.logger.log_request({
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers),
            'body': request.get_data(as_text=True),
            'ip': request.remote_addr
        })

        def custom_start_response(status, headers, exc_info=None):
            # Log response after processing
            self.logger.log_system_event({
                'type': 'response',
                'message': f'Response sent with status {status}',
                'details': {'status': status, 'headers': dict(headers)}
            })
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)

# Example usage with the meter reading API:
def setup_logging_for_meter_api(app: Flask):
    logger = MeterLoggingSystem()
    app.wsgi_app = RequestLoggerMiddleware(app.wsgi_app, logger)
    
    @app.before_request
    def before_request():
        g.start_time = datetime.now()

    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = datetime.now() - g.start_time
            logger.log_system_event({
                'type': 'request_completed',
                'message': f'Request processed in {elapsed.total_seconds()}s',
                'details': {
                    'path': request.path,
                    'method': request.method,
                    'status_code': response.status_code
                }
            })
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.log_error({
            'type': type(e).__name__,
            'message': str(e),
            'stack_trace': traceback.format_exc()
        })
        return jsonify({'error': 'Internal Server Error'}), 500

    return logger

# Example of how to integrate with the main API (Ayushi):
'''
if __name__ == '__main__':
    app = Flask(__name__)
    logger = setup_logging_for_meter_api(app)
    
    @app.route('/api/meter/reading', methods=['POST'])
    def submit_reading():
        try:
            data = request.get_json()
            # Log the meter reading
            logger.log_meter_reading({
                'meter_id': data.get('meter_id'),
                'reading': data.get('reading'),
                'status': 'received'
            })
            # Process the reading...
            return jsonify({'success': True})
        except Exception as e:
            logger.log_error({
                'type': type(e).__name__,
                'message': str(e),
                'stack_trace': traceback.format_exc()
            })
            raise
            '''
'''
To test the API:

Run the Flask application
Access http://localhost:5000/api/meter/simulate 
in your browser to use the simulation interface
'''







