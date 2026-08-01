# CookieConfig

The CookieConfig class defines security cookie configuration for AmritaCore.

## Properties

- `enable_cookie` (bool): Default `True`. Whether to enable Cookie leak detection mechanism
- `cookie` (str): Random 16-character alphanumeric string. Cookie string for security detection

## Description

The CookieConfig class inherits from BaseModel and is exposed as `AmritaConfig.cookie`. It controls the cookie leak detection mechanism used for security checks. The cookie string is auto-generated via `random_alnum_string(16)` when not explicitly provided.
