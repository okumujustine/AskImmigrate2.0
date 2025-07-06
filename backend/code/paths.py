import os

# Root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Backend directory
# BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

# Inside the backend directory
CODE_DIR = os.path.join(ROOT_DIR, "code")
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
APP_CONFIG_FPATH = os.path.join(ROOT_DIR, "config", "config.yaml")
PROMPT_CONFIG_FPATH = os.path.join(ROOT_DIR, "config", "prompt_config.yaml")


# Inside the code directory
GAZETTEER_ENTITIES_FILE_PATH = os.path.join(CODE_DIR, "gazetteer_entities.yaml")
MCP_SERVER_PATH = os.path.join(CODE_DIR, "askimmigration2_mcp.py")
VECTOR_DB_DIR = os.path.join(OUTPUTS_DIR, "vector_db")
CHAT_HISTORY_DB_FPATH = os.path.join(OUTPUTS_DIR, "chat_history.db")