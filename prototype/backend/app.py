from mesh_api import create_application

# Module-level instance so that the `flask run` command detects it automatically
# and to allow direct execution via `python app.py`.
application = create_application()

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
