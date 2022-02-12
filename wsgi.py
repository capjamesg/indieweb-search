from __init__ import create_app
import sys

app = create_app()

if len(sys.argv) > 1 and sys.argv[1] == "--debug":
    app.run(debug=True)