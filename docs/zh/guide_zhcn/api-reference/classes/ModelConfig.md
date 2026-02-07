# ModelConfig

The ModelConfig class defines configuration parameters for the AI model.

## Properties

- `top_k` (int): Default value is 50, TopK parameter controls the model considering the top k most probable words
- `top_p` (float): Default value is 0.95, TopP parameter controls the model considering cumulative probability reaching p of words
- `temperature` (float): Default value is 0.7, temperature parameter controls the randomness of generation
- `stream` (bool): Default value is False, whether to enable streaming response (character-by-character output)
- `thought_chain_model` (bool): Default value is False, whether to enable thought chain model optimization (enhancing complex problem solving)
- `multimodal` (bool): Default value is False, whether to support multimodal input (e.g. image recognition)

## Description

The ModelConfig class inherits from BaseModel and is used to configure behavioral parameters of the AI model. These parameters directly impact the quality and style of AI model outputs and can be adjusted according to specific application scenarios.