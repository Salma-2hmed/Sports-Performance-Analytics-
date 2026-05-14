"""
Sports Performance Analytics - Project 48
Entry point: starts the Flask REST API server
"""

from api.app import create_app

app = create_app()
print("=" * 60)
print("  Sports Performance Analytics API - Project 48")
print("=" * 60)
app.run(debug=True, port=5000)
