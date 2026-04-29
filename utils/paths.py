import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def get_data_path(filename):
    """Returns the absolute path to a file in the data directory."""
    return os.path.join(DATA_DIR, filename)
