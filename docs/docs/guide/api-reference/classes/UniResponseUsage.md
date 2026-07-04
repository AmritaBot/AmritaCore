# UniResponseUsage

UniResponseUsage class represents usage statistics for responses.

## Properties

- `prompt_tokens` (T_INT): Number of tokens used in the prompt
- `completion_tokens` (T_INT): Number of tokens used in the completion (generation)
- `total_tokens` (T_INT): Total number of tokens used
- `cache_creation` (int | None): Number of tokens used to create the cache entry (Anthropic prompt caching)
- `cache_hit` (int | None): Number of tokens read from the cache (Anthropic prompt caching)

## Description

The UniResponseUsage class inherits from BaseModel and implements generics, used to record and track usage information for AI model calls. This information is crucial for monitoring API usage, cost calculation, and performance optimization.

UniResponseUsage is part of AmritaCore's usage management system, helping users understand resource consumption for each AI interaction.
