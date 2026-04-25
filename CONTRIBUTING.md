# Contribution Guide

Thank you for your interest in contributing to AmritaCore! This guide will help you understand how to participate in the project.

## Code of Conduct

Before participating in the project, please read our [Code of Conduct](./CODE_OF_CONDUCT.md) and abide by its provisions.

## AIGC Content Licensing Policy

We welcome the use of AI-generated content as a tool to enhance development efficiency, while maintaining high standards for code quality and integrity:

1. **AI as a Tool**: The use of AI for code generation is recognized as a technological advancement and valuable productivity tool.

2. **Core Business Logic**: All core business logic code must be written manually by developers and undergo thorough code review. AI-generated core business logic will not be accepted.

3. **Documentation**: AI-generated documentation is permitted, but must strictly conform to the project's API definitions and specifications.

4. **Tests**: Test cases may be generated using LLMs, but must provide complete coverage of the corresponding code lines, logical branches, and edge cases.

5. **Review Requirement**: All AI-generated content, regardless of type, must be reviewed and validated by human contributors before submission.

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

## Testing Requirements

### Unit Tests for Functional Changes

When contributing code that introduces new functionality or modifies existing functionality, you are required to include corresponding unit tests:

- **New Features**: All new features must include comprehensive unit tests covering both basic functionality and edge cases
- **Bug Fixes**: Each bug fix must include regression tests that reproduce the reported issue and verify the fix
- **Breaking Changes**: Breaking changes must include tests demonstrating the new behavior and verifying that the change works as intended

### Test Quality Standards

- Write tests that are clear, focused, and easy to understand
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases where applicable
- Test error conditions and boundary values
- Follow the existing test patterns in the codebase

### Running Tests

Before submitting your PR, ensure all tests pass:

```bash
# Run all tests (use python3 as specified in project configuration)
python3 -m pytest tests/

# Run tests with coverage
python3 -m pytest tests/ --cov=amrita_core

# Run specific test file
python3 -m pytest tests/test_specific_module.py

# Or use the provided script
bash scripts/run_test.sh
```

## Development Process

### Code Style

- Use the [PEP 8](https://peps.python.org/pep-0008/) Python code style
- Add type hints
- Write docstrings for all public functions and classes
- Use meaningful variable and function names
- Use ruff for code formatting

### Available Development Scripts

The project provides several helper scripts in the `scripts/` directory:

- **`format.sh`**: Format Python code using ruff (`--check` for dry-run)
- **`lint.sh`**: Lint Python code using ruff (`--fix` to auto-fix issues)
- **`typecheck.sh`**: Run type checking
- **`run_test.sh`**: Run all tests
- **`docs-lint.sh`**: Lint documentation files using Prettier (`--fix` to auto-fix)
- **`docs-dev.sh`**: Start documentation development server
- **`docs-build.sh`**: Build documentation
- **`clean.sh`**: Clean build artifacts and caches
- **`release.sh`**: Prepare release
- **`init_venv.sh`**: Initialize virtual environment
- **`check.sh`**: Run comprehensive checks (format, lint, typecheck, test)

Before submitting a PR, it's recommended to run:

```bash
bash scripts/check.sh
```

### Documentation

- Update relevant documentation in the `docs/` directory
- Add examples for new features
- Keep documentation synchronized with code
- Both English and Chinese documentation should be updated simultaneously

## Project Structure

```text
AmritaCore/
├── src/
│   └── amrita_core/          # Core source code
│       ├── agent/            # Agent core logic
│       │   ├── context.py    # Context management
│       │   ├── functions.py  # Function calling logic
│       │   └── strategy.py   # Execution strategies
│       ├── builtins/         # Built-in components
│       │   ...
│       ├── hook/             # Event hook system
│       │   ├── event.py      # Event definitions
│       │   ├── matcher.py    # Event matchers
│       │   └── on.py         # Hook decorators/registration
│       ├── tools/            # Tool management system
│       │   ├── manager.py    # Tool registration and dispatch
│       │   └── mcp.py        # MCP client integration
│       ├── __init__.py       # Entry point
│       ├── chatmanager.py    # Chat manager
│       ├── config.py         # Configuration system
│       ├── consts.py         # Constants
│       ├── libchat.py        # Chat library
│       ├── logging.py        # Logging system
│       ├── preset.py         # Preset manager
│       ├── protocol.py       # Protocol layer
│       ├── sessions.py       # Session management
│       ├── streaming.py      # Streaming utilities
│       ├── threadsafe.py     # Thread safety utilities
│       ├── tokenizer.py      # Tokenizer
│       ├── types.py          # Type definitions
│       └── utils.py          # Utility functions
├── demo/                     # Example code
├── docs/                     # Documentation
│   └── zh/                   # Chinese documentation
├── tests/                    # Test code
├── scripts/                  # Development scripts
└── pyproject.toml           # Project configuration
```

## Code Contribution Examples

### Adding New Features

1. Create a new module in `src/amrita_core/` or extend existing modules
2. Add type definitions to `types.py` (if needed)
3. Implement the feature ensuring it follows existing code style
4. Add unit tests
5. Update documentation (both English and Chinese)

### Fixing Bugs

1. Identify the problem
2. Create a test case to verify the issue
3. Fix the issue
4. Ensure all tests pass

### Improving Documentation

- Update relevant documentation in the `docs/` directory
- Ensure grammar is correct and content is clear
- Follow existing documentation structure
- Update both English and Chinese versions simultaneously

## Contact Us

- Discord: [Discord Server](https://discord.gg/byAD3sbjjj)
- QQ Group: 1006893368
- Email: [admin@suggar.top](mailto:admin@suggar.top)

## Acknowledgments

Thank you to all community members who have contributed to AmritaCore!
