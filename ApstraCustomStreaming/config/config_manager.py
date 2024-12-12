# config/config_manager.py
import yaml
import os
from pathlib import Path
from .schema import CONFIG_SCHEMA

def load_yaml_file(file_path):
    """Load and parse a YAML file."""
    try:
        with open(file_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file {file_path}: {e}")

def validate_type(value, expected_type):
    """Validate that a value matches expected type."""
    if expected_type == bool and isinstance(value, int):
        return bool(value)
    if not isinstance(value, expected_type):
        try:
            return expected_type(value)
        except (ValueError, TypeError):
            return None
    return value

def validate_config_section(config, schema, path=""):
    """Validate a config section against its schema."""
    errors = []
    validated = {}

    # Check required fields
    for field, field_type in schema.get('required', {}).items():
        current_path = f"{path}.{field}" if path else field
        value = config.get(field)
        
        if value is None:
            errors.append(f"Missing required field: {current_path}")
            continue
            
        validated_value = validate_type(value, field_type)
        if validated_value is None:
            errors.append(f"Invalid type for {current_path}. Expected {field_type.__name__}")
        else:
            validated[field] = validated_value

    # Process optional fields
    for field, (default_value, field_type) in schema.get('optional', {}).items():
        current_path = f"{path}.{field}" if path else field
        value = config.get(field, default_value)
        
        validated_value = validate_type(value, field_type)
        if validated_value is not None:
            validated[field] = validated_value
        else:
            validated[field] = default_value

    return validated, errors

def load_config(config_dir=None):
    """Load and validate all configuration."""
    if config_dir is None:
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        config_dir = current_dir / 'settings'
    else:
        config_dir = Path(config_dir)

    # Load all config files
    configs = {
        'redis': load_yaml_file(config_dir / 'redis.yml'),
        'apstra_api': load_yaml_file(config_dir / 'apstra_api.yml'),
        'outputs': load_yaml_file(config_dir / 'outputs.yml')
    }

    # Add environment variables for sensitive data
    configs['apstra_api']['apstra_api'].update({
        'username': os.getenv('APSTRA_USERNAME', configs['apstra_api'].get('username')),
        'password': os.getenv('APSTRA_PASSWORD', configs['apstra_api'].get('password')),
    })

    # Validate each section
    validated_config = {}
    all_errors = []

    # Validate redis config
    redis_config, redis_errors = validate_config_section(
        configs['redis'].get('redis', {}),
        CONFIG_SCHEMA['redis'],
        'redis'
    )
    validated_config['redis'] = redis_config
    all_errors.extend(redis_errors)

    # Validate apstra_api config
    apstra_api_config, apstra_api_errors = validate_config_section(
        configs['apstra_api'].get('apstra_api', {}),
        CONFIG_SCHEMA['apstra_api'],
        'apstra_api'
    )
    validated_config['apstra_api'] = apstra_api_config
    all_errors.extend(apstra_api_errors)

    # Validate outputs
    validated_config['outputs'] = {}
    outputs_config = configs['outputs'].get('outputs', {})

    for output_type in ['syslog', 'webhook']:
        if output_type in outputs_config:
            output_config, output_errors = validate_config_section(
                outputs_config[output_type],
                CONFIG_SCHEMA['outputs'][output_type],
                f'outputs.{output_type}'
            )
            validated_config['outputs'][output_type] = output_config
            all_errors.extend(output_errors)

    if all_errors:
        raise ValueError(f"Configuration errors found:\n" + "\n".join(all_errors))

    return validated_config

def get_redis_config(config=None):
    """Get Redis configuration."""
    if config is None:
        config = load_config()
    return config['redis']

def get_apstra_api_config(config=None):
    """Get apstra_api configuration."""
    if config is None:
        config = load_config()
    return config['apstra_api']

def get_output_config(output_name, config=None):
    """Get output configuration."""
    if config is None:
        config = load_config()
    return config['outputs'].get(output_name, {})

def is_output_enabled(output_name, config=None):
    """Check if an output is enabled."""
    output_config = get_output_config(output_name, config)
    return output_config.get('enabled', False)


