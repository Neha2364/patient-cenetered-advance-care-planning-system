import os
from flask import Flask, jsonify, render_template_string, request, make_response
from flask_cors import CORS
from backend.config import Config
from backend.extensions import db, ma
from backend.routes import register_routes
from backend import models

def create_app(config_class=Config):
    """Application factory for the Advance Care Planning (ACP) System backend."""
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 1. Load config
    app.config.from_object(config_class)
    
    # 2. Validate configuration (requires Supabase connection strings, keys, etc.)
    # In testing environment, we might skip strict validation to allow mock databases
    if app.config['ENV'] != 'testing':
        config_class.validate()

    # 3. Initialize Flask extensions
    db.init_app(app)
    ma.init_app(app)

    # 4. Register routes & blueprints
    register_routes(app)

    # 5. Serve OpenAPI Spec & Swagger UI
    @app.route('/docs')
    @app.route('/api/docs')
    def swagger_ui():
        """Serve dynamic CDN-based Swagger UI for API documentation."""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>ACP Backend API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui.css" />
            <link rel="icon" type="image/png" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/favicon-32x32.png" sizes="32x32" />
            <style>
                html { box-sizing: border-box; overflow:-y-scroll; }
                *, *:before, *:after { box-sizing: inherit; }
                body { margin: 0; background: #fafafa; }
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-bundle.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-standalone-preset.js"></script>
            <script>
                window.onload = function() {
                    const ui = SwaggerUIBundle({
                        url: "/static/openapi.json",
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.SwaggerUIStandalonePreset
                        ],
                        plugins: [
                            SwaggerUIBundle.plugins.DownloadUrl
                        ],
                        layout: "BaseLayout"
                    });
                    window.ui = ui;
                };
            </script>
        </body>
        </html>
        """
        return render_template_string(html_content)

    # 6. Database tables creation hook
    with app.app_context():
        # Creates tables if they don't exist in Supabase PostgreSQL
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=app.config['PORT'])
