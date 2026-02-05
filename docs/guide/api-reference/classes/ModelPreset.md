# ModelPreset

The ModelPreset class defines the preset configuration for AI models.

## Properties

- `model` (str): Name of the AI model (e.g. gpt-3.5-turbo)
- `name` (str): Identifier name for current preset, defaults to "default"
- `base_url` (str): Base address of API service (uses OpenAI default if empty)
- `api_key` (str): Key required to access API
- `protocol` (str): Protocol adapter type, defaults to "__main__"
- `config` ([ModelConfig](ModelConfig.md)): Model configuration object
- `extra` (dict[str, Any]): Extra configuration items

## Methods

- `load(path: Path)`: Load model preset configuration from the specified path
- `save(path: Path)`: Save current preset configuration to the specified path

## Description

The ModelPreset class inherits from BaseModel and is used to encapsulate complete configuration information for AI models. It not only includes basic model parameters but also provides functionality to load and save configuration files, facilitating management and reuse of different model configurations.