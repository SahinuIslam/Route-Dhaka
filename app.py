"""Start the desktop app:

    python app.py                 # opens the Dhaka data set
    python app.py --data sample   # opens the 11-stop sample
    python app.py --mode Dark     # Light, Dark or System (default)
"""
import sys

try:
    import tkinter  # noqa: F401
except ImportError:
    sys.exit("Tkinter is missing from this Python. On Windows/macOS reinstall Python from python.org "
             "(it includes Tkinter). On Ubuntu: sudo apt install python3-tk")
try:
    import customtkinter  # noqa: F401
except ImportError:
    sys.exit("CustomTkinter is not installed. Activate the virtual environment and run:\n"
             "    pip install -r requirements.txt")

from src.gui.app import main

if __name__ == "__main__":
    main()
