# MLArgParser

MLArgParser is a multi-level argument parser for building CLI applications in Python. It maps object-oriented concepts directly to the command line: subclasses become subcommands, methods become commands, and method parameters become command-line arguments. Type hints and docstrings drive help text and type conversion automatically.

**Requirements:** Python 3.8+ (3.9+ recommended for `exit_on_error=False` and built-in generics like `list[str]`).


## Design

- **Commands** are the public methods of your parser class (names not starting with `_`).
- **Arguments** are the parameters of those methods; names and types come from the signature.
- **Help text** comes from the class/method docstrings and from the `arg_desc` dictionary.
- **Subcommands** are implemented by assigning another `MLArgParser` subclass as a class attribute, forming a tree of commands.

The library uses [argparse](https://docs.python.org/3/library/argparse.html) under the hood. You get standard help formatting, long and short options, and consistent error handling without writing parser setup code by hand.


## Quick start

Subclass `MLArgParser` and define methods; their names become commands. Use type hints and defaults for arguments; use `arg_desc` to describe them in help.

```python
#!/usr/bin/env python3

from mlargparser import MLArgParser


class MyApp(MLArgParser):
    """My application."""

    arg_desc = {
        "count": "Number of items",
        "name": "Item name",
        "format": "Output format",
    }

    def list_(self, count: int = 10, name: str = None):
        """List items."""
        print(f"count={count}, name={name}")

    def run(self, format: str = "text"):
        """Run the task."""
        print(f"format={format}")


if __name__ == "__main__":
    MyApp()
```

Example invocations:

```text
./myapp.py --help
./myapp.py list --count 5 --name foo
./myapp.py run --format json
```

Public method names are normalized for the CLI: underscores become dashes, and by default command names are lowercased (e.g. `list_` becomes `list`).


## Commands and arguments

### Commands

Every public method (no leading `_`) is a command. The command name is derived from the method name: underscores are replaced with dashes, and by default the result is lowercased (e.g. `dump_config` becomes `dump-config`).

### Argument types

Parameter type hints determine how values are parsed and passed to your method:

| Annotation   | CLI behavior                          |
|-------------|----------------------------------------|
| `str`       | One string (default if no annotation)  |
| `int`       | One integer                           |
| `float`     | One float                             |
| `bool`      | Flag; see Boolean flags below         |
| `list[T]`   | One or more values, collected as list |
| `set[T]`    | One or more values, collected as set  |
| `tuple[T, ...]` | One or more values, as tuple    |
| `Optional[T]` / `Union[T, None]` | Unwraps to `T`        |

Unannotated parameters and `None` are treated as `str`. Invalid or unresolved annotations are reported at startup when `strict_types=True` (default).

### Required and optional

- No default (or `inspect.Parameter.empty`) means the argument is **required**.
- A default value makes the argument optional; the default is shown in help.

### Argument descriptions

Set `arg_desc` on your class (or subclass) to map parameter names to help strings:

```python
arg_desc = {
    "count": "Number of items to process",
    "output": "Output file path",
}
```

If a parameter is not in `arg_desc`, help uses the placeholder `FIXME: UNDOCUMENTED`. Subparsers merge their parent’s `arg_desc` with their own; local entries override the parent’s for the same key.


## Boolean flags

Boolean parameters are turned into flags:

- **Default `False`:** one flag that turns the value to `True` (e.g. `--verbose`).
- **Default `True`:** one flag that turns it to `True` (redundant but explicit) and, by default, a `--no-<name>` flag that turns it to `False` (e.g. `--no-cache`).
- **Parameter name starts with `no_`:** treated as the “off” side of a flag; the option is `--no-<rest>` and sets the *base* name to `False` (e.g. `no_cache` -> `--no-cache` and `dest` `cache`).

You must not define both a `foo` and a `no_foo` parameter for the same logical flag; that is rejected as ambiguous. Set `auto_disable_flags = False` on your class to disable automatic `--no-*` generation for `True`-default booleans.


## Subcommands (command trees)

To add a subcommand level, assign an `MLArgParser` subclass as a **class attribute**. That class is then instantiated when the user selects that command; it parses the rest of `argv` and dispatches to its own commands.

Example: one top-level command `dump` with subcommands `config`, `state`, and `authtoken`:

```python
class DumpCmd(MLArgParser):
    """Dump subcommand."""

    def config(self):
        """Dump configuration."""
        ...

    def state(self):
        """Dump state."""
        ...

    def authtoken(self):
        """Dump auth token."""
        ...


class MyApp(MLArgParser):
    """Main application."""
    dump = DumpCmd
```

Invocation:

```text
./app.py dump config
./app.py dump state
./app.py dump authtoken
```

When the user runs `./app.py dump config`, the top-level parser sees the command `dump`, gets the class `DumpCmd`, and calls `DumpCmd(level=2, parent=app, top=app)`. That sub-parser then parses `config` and invokes `DumpCmd.config()`. You can nest further by assigning another parser class as an attribute of `DumpCmd`, and so on.

Inside a subcommand, `self.parent` is the immediate parent parser instance and `self.top` is the root parser instance (e.g. `MyApp`), which is useful for sharing state or configuration.


## Options (short and long)

For each argument the library adds a long option `--<name>` (with underscores in the name turned into dashes). If the first character of the argument name is not already used by another argument, a short option `-<letter>` is also added. So for a parameter `verbose`, you get both `--verbose` and `-v` unless `-v` was already taken.


## Configuration

Set these as class attributes on your parser class (or subclass):

| Attribute               | Default   | Description |
|-------------------------|-----------|-------------|
| `arg_desc`              | `None`    | Dict mapping parameter names to help strings. |
| `auto_disable_flags`    | `True`    | If `True`, add `--no-<name>` for boolean parameters with default `True`. |
| `case_sensitive_commands`| `False`   | If `True`, command names are not lowercased. |
| `strict_validation`     | `True`    | If `True`, command name collisions and (when `strict_types` is also `True`) type validation errors are fatal. |
| `strict_types`          | `True`    | If `True`, invalid or unresolved type annotations cause startup to fail; if `False`, they are reported as warnings. |

Constructor:

- `MLArgParser(level=1, parent=None, top=None, noparse=False, strict_types=True)`  
  Normally you do not call this with custom `level`/`parent`/`top`; they are used internally for subcommands. Use `noparse=True` only in tests or when you need to set up the parser without parsing `sys.argv` (e.g. to build help or run a specific command programmatically).


## Help output

- The top-level description is the class docstring.
- Each command’s description is that method’s docstring.
- Each argument’s help comes from `arg_desc` or the undocumented placeholder.
- Defaults are appended where applicable (e.g. `[default: "text"]`, `[enabled by default]`).


## Testing

Tests live under `tests/` and use the standard library `unittest`:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```


## License

Unless otherwise noted, code in this repository is licensed under the LGPL v2 only. For use under a different license, contact the author.


## References

- [argparse](https://docs.python.org/3/library/argparse.html) — Python standard library.
- [PEP 484](https://peps.python.org/pep-0484/) — Type hints.
- Implementation inspired by [Multi-level argparse](https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html).
