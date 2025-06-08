from pathlib import Path
from dotenv import load_dotenv

# Get absolute path to the current file
CURRENT_FILE = Path(__file__).resolve()

# Automatically find the project root
def find_project_root(marker_files=(".git", "project_config.yaml", ".env")):
    path = CURRENT_FILE
    while path != path.parent:
        if any((path / marker).exists() for marker in marker_files):
            return path
        path = path.parent
    return CURRENT_FILE.parent.parent.parent

# Project root directory
ROOT_DIR = find_project_root()

# Load .env from root if exists
dotenv_path = ROOT_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path) # loads the .env only once


# Define commonly used paths
DATA_DIR = ROOT_DIR / "data"
ML_DIR = ROOT_DIR / "ml"
LOGS_DIR = ROOT_DIR / "logs"
CONFIG_PATH = ROOT_DIR / "config"
MODELS_PATH = ML_DIR / "models"

def build_path_from_root(*names):
    """function to build any relative path from root"""
    return ROOT_DIR.joinpath(*names)

def build_relative_path(from_dir: Path, *names):
    """function to build any relative path from specific directory"""
    return from_dir.joinpath(*names)