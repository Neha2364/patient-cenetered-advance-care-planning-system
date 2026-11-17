from flask import jsonify
from backend.routes.api import api_bp

def register_routes(app):
    """Register Blueprints and configure system-wide API error handlers."""
    
    # Register core API routes
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Global HTTP Error Handlers
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource could not be found.'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method Not Allowed', 'message': 'The HTTP method used is not supported for this endpoint.'}), 405

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad Request', 'message': 'The server could not understand the request due to invalid syntax.'}), 400

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred on the server.'}), 500
