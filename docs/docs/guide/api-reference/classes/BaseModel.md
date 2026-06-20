# BaseModel

The BaseModel class is the base class for all data models in AmritaCore, inheriting from Pydantic's BaseModel.

## Description

The BaseModel class provides extensions to Pydantic BaseModel, adding dictionary-style access capabilities (duck typing):

- `__str__` and `__repr__`: Convert the model to JSON string
- `__getitem__` and `__setitem__`: Allow dictionary-style access and setting of model fields
- Retains all validation and serialization features of Pydantic

## Features

- Supports model validation and data serialization
- Supports dictionary-style access methods
- Supports JSON serialization and deserialization
- Integrates Pydantic's Field definition functionality

## Related Classes

- [`DirtyAwareBaseModel`](DirtyAwareBaseModel.md): Extends BaseModel with automatic dirty-mark tracking for mutation detection — useful for backends that need to know which fields changed

## Usage

BaseModel is the base class for all data models and should not be instantiated directly. It is inherited by other model classes (such as Message, ModelConfig, etc.) for use.
