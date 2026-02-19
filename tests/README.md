# MLArgParser Test Suite

This directory contains comprehensive tests for the MLArgParser library.

## Test Organization

Tests are organized by feature area:

- **test_basic_parsing.py** - Basic command parsing, argument types, default values
- **test_boolean_flags.py** - Boolean flag handling, auto-disable flags, descriptions
- **test_collection_types.py** - List, set, tuple, dict types and flattening
- **test_type_validation.py** - Type validation, error handling, strict modes
- **test_command_collisions.py** - Command name collisions, suggestions, boolean collisions
- **test_subcommands.py** - Subcommand functionality, inheritance
- **test_options.py** - Short and long option handling
- **test_arg_descriptions.py** - Argument description handling, inheritance
- **test_error_handling.py** - Error cases, edge cases, help text
- **test_integration.py** - End-to-end workflows, real-world scenarios
- **test_cmdarg.py** - CmdArg class unit tests

## Running Tests

### Run all tests:
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Run specific test file:
```bash
python3 -m unittest tests.test_basic_parsing -v
```

### Run specific test class:
```bash
python3 -m unittest tests.test_basic_parsing.TestBasicCommandParsing -v
```

### Run specific test:
```bash
python3 -m unittest tests.test_basic_parsing.TestBasicCommandParsing.test_simple_command -v
```

## Test Coverage

The test suite covers:

### Core Functionality
- ✅ Basic command parsing and execution
- ✅ All argument types (str, int, float, bool, list, set, tuple, dict)
- ✅ Optional and required arguments
- ✅ Default values
- ✅ Type conversion

### Boolean Flags
- ✅ Boolean with False default (store_true)
- ✅ Boolean with True default (store_true + auto --no-* flag)
- ✅ no_ prefix parameters (store_false)
- ✅ Auto-disable flag generation
- ✅ Flag descriptions and help text

### Collection Types
- ✅ List types (list[str], list[int])
- ✅ Set types (set[str])
- ✅ Tuple types (tuple[str, ...])
- ✅ Multiple invocations flattening
- ✅ Nested list flattening
- ✅ Optional collections

### Type Validation
- ✅ TypeValidator utility methods
- ✅ Invalid type detection
- ✅ String annotation handling
- ✅ Strict vs non-strict modes
- ✅ Complex type annotations (Union, Optional)

### Command Management
- ✅ Command name collisions
- ✅ Case sensitivity
- ✅ Underscore/dash normalization
- ✅ Command suggestions
- ✅ Boolean parameter collisions

### Subcommands
- ✅ Basic subcommand structure
- ✅ arg_desc inheritance
- ✅ Level tracking
- ✅ Nested subcommands

### Options
- ✅ Long options (--option)
- ✅ Short options (-o)
- ✅ Option collision handling
- ✅ Underscore to dash conversion

### Argument Descriptions
- ✅ arg_desc dictionary
- ✅ Description inheritance
- ✅ Default value in descriptions
- ✅ Validation of arg_desc keys

### Error Handling
- ✅ Invalid commands
- ✅ Missing required arguments
- ✅ Invalid type conversions
- ✅ Edge cases (empty lists, None defaults)
- ✅ Help text generation

### Integration
- ✅ Complex workflows
- ✅ Multiple commands
- ✅ Real-world scenarios (git-like, docker-like interfaces)

## Test Statistics

- **Total test files**: 11
- **Total test cases**: 100+
- **Coverage areas**: All major features and edge cases

## Notes

- Some tests may produce expected errors (e.g., invalid arguments) - these are intentional
- Tests use `noparse=True` to avoid actual command execution where only parser setup is needed
- Tests use `unittest.mock.patch` to control `sys.argv` for command-line argument testing
