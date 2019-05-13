import os.path as osp
import shutil

import yaml

from labelme.logger import logger


here = osp.dirname(osp.abspath(__file__))


def update_dict(target_dict, new_dict, validate_item=None):
    for key, value in new_dict.items():
        if validate_item:
            validate_item(key, value)
        if key not in target_dict:
            logger.warn('Skipping unexpected key in config: {}'
                        .format(key))
            continue
        if isinstance(target_dict[key], dict) and \
                isinstance(value, dict):
            update_dict(target_dict[key], value, validate_item=validate_item)
        else:
            target_dict[key] = value


# -----------------------------------------------------------------------------


def get_default_config():
    config_file = osp.join(here, 'default_config.yaml')
    with open(config_file) as f:
        config = yaml.load(f)

    # save default config to ~/.labelmerc
    user_config_file = osp.join(osp.expanduser('~'), '.labelmerc')
    if not osp.exists(user_config_file):
        try:
            shutil.copy(config_file, user_config_file)
        except Exception:
            logger.warn('Failed to save config: {}'.format(user_config_file))

    return config


def validate_config_item(key, value):
    if key == 'validate_label' and value not in [None, 'exact', 'instance']:
        raise ValueError(
            "Unexpected value for config key 'validate_label': {}"
            .format(value)
        )
    if key == 'labels' and value is not None and len(value) != len(set(value)):
        raise ValueError(
            "Duplicates are detected for config key 'labels': {}".format(value)
        )


def get_config(config_from_args=None, config_file=None):
    # Configuration load order:
    #
    #   1. default config (lowest priority)
    #   2. config file passed by command line argument or ~/.labelmerc
    #   3. command line argument (highest priority)

    # 1. default config
    config = get_default_config()

    # 2. config from yaml file
    if config_file is not None and osp.exists(config_file):
        with open(config_file) as f:
            user_config = yaml.load(f) or {}
        update_dict(config, user_config, validate_item=validate_config_item)

    # 3. command line argument
    if config_from_args is not None:
        update_dict(config, config_from_args,
                    validate_item=validate_config_item)

    return config

def get_default_directory_config(config):
    return config['default_directory_config']

def get_directory_config(config, config_file=None):
    # Configuration load order:
    #
    #   1. default config
    #   2. config file from input directory

    # 1. default config
    directory_config = get_default_directory_config(config)

    # 2. config from yaml file
    if config_file is not None:
        if osp.exists(config_file):
            with open(config_file) as f:
                user_config = yaml.load(f) or {}
            update_dict(directory_config, user_config, validate_item=validate_config_item)
        else:
            with open(config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)

    return directory_config