#!/usr/bin/env python3
"""
Optional bash/zsh tab completion for MLArgParser via argcomplete.

This module is optional and does not require argcomplete to be installed.
When argcomplete is installed and install() is called, MLArgParser is patched
so that completion runs before normal parsing when _ARGCOMPLETE is set.
"""

import argparse
import inspect
import os
import sys

try:
    import argcomplete
except ImportError:
    argcomplete = None

ARGCOMPLETE_AVAILABLE = argcomplete is not None


def _copy_parser_content(source_parser, target_parser):
    """Copy actions and subparsers from source_parser into target_parser."""
    for action in source_parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sp = target_parser.add_subparsers(dest=action.dest)
            for name, child_parser in action.choices.items():
                desc = getattr(child_parser, "description", None)
                new_p = sp.add_parser(name, description=desc)
                _copy_parser_content(child_parser, new_p)
        elif getattr(action, "dest", None) == "help":
            continue
        else:
            kwargs = {}
            for key in ("dest", "type", "choices", "required", "help", "metavar", "action", "nargs"):
                val = getattr(action, key, None)
                if val is not None:
                    kwargs[key] = val
            if hasattr(action, "default"):
                kwargs["default"] = action.default
            try:
                target_parser.add_argument(*action.option_strings, **kwargs)
            except TypeError:
                # Drop kwargs that this action type doesn't support
                for drop in ("type", "choices", "nargs"):
                    kwargs.pop(drop, None)
                target_parser.add_argument(*action.option_strings, **kwargs)


def build_completion_parser(instance):
    """
    Build an argparse.ArgumentParser tree that mirrors this MLArgParser's CLI.

    The instance must have been constructed with noparse=True and must have
    had __init_commands() and __merge_arg_desc() run (so instance.commands
    and instance.arg_desc are populated).

    Returns a single ArgumentParser with subparsers at each level, suitable
    for passing to argcomplete.autocomplete().
    """
    if instance.short_options is None:
        instance.short_options = []

    level = instance.level
    argv_slice = sys.argv[0:level] if len(sys.argv) >= level else sys.argv
    usage_str = (("%s " * len(argv_slice)) + "<command> [<args>]") % tuple(argv_slice)

    root = argparse.ArgumentParser(
        description=inspect.getdoc(instance),
        usage=usage_str,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = root.add_subparsers(dest="command")

    for cmd_name, (attr_name, callable_obj) in instance.commands.items():
        if isinstance(callable_obj, type):
            # Subcommand class (e.g. DumpCmd)
            subp = subparsers.add_parser(cmd_name)
            top = instance.top if instance.level > 1 else instance
            nested = callable_obj(
                noparse=True,
                level=instance.level + 1,
                parent=instance,
                top=top,
                strict_types=instance.strict_types,
            )
            nested._MLArgParser__init_commands()
            nested._MLArgParser__merge_arg_desc()
            nested_parser = build_completion_parser(nested)
            # Nested parser has one level of subparsers; graft it onto subp
            _copy_parser_content(nested_parser, subp)
        else:
            # Method command
            subp = subparsers.add_parser(cmd_name, description=inspect.getdoc(callable_obj))
            req_group = subp.add_argument_group("required arguments")
            defaults = {}
            for arg, default_val in instance._MLArgParser__get_arg_properties(callable_obj):
                options = instance._MLArgParser__get_options_for_arg(arg.name)
                kwargs = arg.get_argparse_kwargs()
                grp = req_group if arg.required else subp
                grp.add_argument(*options, **kwargs)
                if default_val not in (None, inspect.Parameter.empty):
                    defaults[arg.name] = default_val
            subp.set_defaults(**defaults)

    return root


_original_init = None


def install():
    """
    Enable argcomplete for MLArgParser by patching __init__.

    When argcomplete is installed and the process is run under completion
    (_ARGCOMPLETE in the environment), the first MLArgParser(root) instantiation
    will build the completion parser, call argcomplete.autocomplete(parser),
    and exit. Otherwise normal parsing runs.

    Idempotent: safe to call multiple times. No-op if argcomplete is not installed.
    """
    global _original_init
    if argcomplete is None:
        return

    from mlargparser import MLArgParser

    if _original_init is not None:
        return

    _original_init = MLArgParser.__init__

    def _patched_init(self, level=1, parent=None, top=None, noparse=False, strict_types=True):
        if os.environ.get("_ARGCOMPLETE") and level == 1:
            # Run completion path: build parser, autocomplete, exit
            _original_init(self, level=1, parent=None, top=None, noparse=True, strict_types=strict_types)
            self._MLArgParser__init_commands()
            self._MLArgParser__merge_arg_desc()
            parser = build_completion_parser(self)
            argcomplete.autocomplete(parser, exit_method=os._exit)
            return
        _original_init(self, level=level, parent=parent, top=top, noparse=noparse, strict_types=strict_types)

    MLArgParser.__init__ = _patched_init


def uninstall():
    """Restore the original MLArgParser.__init__. No-op if not patched."""
    global _original_init
    if _original_init is None:
        return
    from mlargparser import MLArgParser
    MLArgParser.__init__ = _original_init
    _original_init = None
