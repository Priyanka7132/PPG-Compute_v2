import logging
import sys
import os
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from ppg import create_app
application = create_app(None)