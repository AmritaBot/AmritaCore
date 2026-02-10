# Contribution Guide

Thank you for your interest in contributing to AmritaCore! This guide will help you understand how to participate in the project.

## Code of Conduct

Before participating in the project, please read our [Code of Conduct](./CODE_OF_CONDUCT.md) and abide by its provisions.

## Setting Up the Development Environment

1. Fork the repository to your account
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/AmritaCore.git
   cd AmritaCore
   ```

3. Install dependencies:

   ```bash
   # Using uv (recommended)
   uv venv
   uv sync

   # Or using pip
   pip install -e .
   ```

## How to Contribute

### Reporting Bugs

1. Search the [Issues](https://github.com/AmritaBot/AmritaCore/issues) page to see if a similar bug report already exists
2. If not, create a new issue containing:
   - Detailed bug description
   - Reproduction steps
   - Expected behavior
   - Actual behavior
   - Environment information (OS, Python version, AmritaCore version, etc.)
   - Relevant error messages or screenshots

### Submitting Feature Requests

1. Search the [Issues](https://github.com/AmritaBot/AmritaCore/issues) page to see if a similar feature request already exists
2. If not, create a new issue describing:
   - Feature requirements
   - Why this feature would be useful
   - How this feature would be used
   - Possible implementation approaches

### Submitting Code

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature` or `git checkout -b fix/BugFix`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

### Pull Request Guidelines

- Ensure your PR has a clear description explaining what changes were made and why
- Follow the [PEP 8](https://peps.python.org/pep-0008/) Python code style
- Add necessary tests
- Make sure all tests pass
- Update documentation (if needed)
- If the PR resolves an issue, reference it in the PR (e.g. `Fixes #123`)

## Development Process

### Code Style

- Use the [PEP 8](https://peps.python.org/pep-0008/) Python code style
- Add type hints
- Write docstrings for all public functions and classes
- Use meaningful variable and function names
- Use ruff for code formatting

### Documentation

- Update relevant documentation
- Add examples for new features
- Keep documentation synchronized with code

## Project Structure

```text
AmritaCore/
├── src/
│   └── amrita_core/          # Core source code
│       ├── builtins/         # Built-in functionality
│       ├── hook/             # Event hook system
│       ├── tools/            # Tool system
│       ├── __init__.py       # Entry point
│       ├── chatmanager.py    # Chat manager
│       ├── config.py         # Configuration system
│       ├── libchat.py        # Chat library
│       ├── logging.py        # Logging system
│       ├── preset.py         # Preset manager
│       ├── protocol.py       # Protocol layer
│       ├── tokenizer.py      # Tokenizer
│       ├── types.py          # Type definitions
│       └── utils.py          # Utility functions
├── demo/                     # Example code
├── docs/                     # Documentation
│   └── zh/                   # Chinese documentation
├── tests/                    # Test code
└── pyproject.toml           # Project configuration
```

## Code Contribution Examples

### Adding New Features

1. Create a new module in `src/amrita_core/` or extend existing modules
2. Add type definitions to `types.py` (if needed)
3. Implement the feature ensuring it follows existing code style
4. Add unit tests
5. Update documentation

### Fixing Bugs

1. Identify the problem
2. Create a test case to verify the issue
3. Make sure all tests pass

### Improving Documentation

- Update relevant documentation in the `docs/` directory
- Ensure grammar is correct and content is clear
- Follow existing documentation structure

## Contact Us

- Discord: [Discord Server](https://discord.gg/byAD3sbjjj)
- QQ Group: 1006893368
- Email: [admin@suggar.top](mailto:admin@suggar.top)

## Acknowledgments

Thank you to all community members who have contributed to AmritaCore!
