from __init__ import create_app
import sys

app = create_app()

# if --debug flag is provided, run in debug mode

if sys.argv[1] == "--debug":
    app.run(debug=True)
else:
    app.run()
