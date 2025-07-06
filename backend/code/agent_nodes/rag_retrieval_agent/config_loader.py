from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_yaml_config


def load_app_config():
    return load_yaml_config(APP_CONFIG_FPATH)


def load_prompt_config():
    return load_yaml_config(PROMPT_CONFIG_FPATH)