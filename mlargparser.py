#!/usr/bin/env python3

# Project URL: https://github.com/jpsutton/sandbox/tree/master/mlargparser
# This implementation inspired by https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

# Standard Library
import argparse
import sys
import shutil
import os
import ast
import inspect

from types import GenericAlias

# Try to import typing inspection utilities (Python 3.8+)
try:
    from typing import get_origin, get_args
    HAS_TYPING_INSPECT = True
except ImportError:
    HAS_TYPING_INSPECT = False

    def get_origin(tp):
        return getattr(tp, '__origin__', None)

    def get_args(tp):
        return getattr(tp, '__args__', ())

# string to use for undocumented commands/arguments
STR_UNDOCUMENTED = "FIXME: UNDOCUMENTED"

# list of types that can be safely converted from string by the ast.literal_eval method
AST_TYPES = [list, tuple, dict, set]

# Set this environment variable to help the argparse formatter wrap the lines
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)


class TypeValidator:
    """Utility class for validating and normalizing type annotations."""
    
    @staticmethod
    def is_bool_type(annotation):
        """Check if annotation represents a boolean type."""
        if annotation == bool:
            return True
        
        # Handle Optional[bool]
        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            if args:
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1 and non_none_args[0] == bool:
                    return True
        
        return False
    
    @staticmethod
    def is_valid_annotation(annotation):
        """
        Check if annotation is valid for argument parsing.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Missing annotation is okay (defaults to str)
        if annotation == inspect.Parameter.empty:
            return True, None
        
        # None is okay (defaults to str)
        if annotation is None:
            return True, None
        
        # String annotations need special handling
        if isinstance(annotation, str):
            return False, f"String annotation '{annotation}' cannot be resolved. Use actual type."
        
        # Check if it's a type or callable
        if not (callable(annotation) or hasattr(annotation, '__origin__')):
            return False, f"Annotation {annotation} is neither a type nor callable"
        
        return True, None
    
    @staticmethod
    def normalize_annotation(annotation):
        """
        Normalize annotation to a usable type.
        
        Returns the annotation or a default (str) if empty/None.
        """
        if annotation == inspect.Parameter.empty or annotation is None:
            return str
        
        return annotation


class CmdArg:
    def __resolve_string_annotation(self, annotation):
        """Resolve a string annotation to an actual type."""
        try:
            import builtins
            return getattr(builtins, annotation)
        except AttributeError:
            raise ValueError(f"Cannot resolve string annotation: {annotation}")
    
    def __normalize_typing_with_inspect(self, annotation):
        """Normalize typing annotation using typing inspection utilities (Python 3.8+)."""
        origin = get_origin(annotation)
        if origin is None:
            return None
        
        args = get_args(annotation)
        
        # Handle Optional[T] / Union[T, None]
        try:
            from typing import Union
            if origin is Union and args:
                # Get first non-None type
                for arg in args:
                    if arg is not type(None):
                        return self.__normalize_type_annotation(arg)
        except ImportError:
            pass
        
        # Handle List[T], Set[T], Tuple[T], etc.
        if origin in (list, set, tuple, dict):
            if args:
                return self.__normalize_type_annotation(args[0])
            return origin
        
        return None
    
    def __normalize_typing_fallback(self, annotation):
        """Normalize typing annotation using fallback method for older Python versions."""
        origin = getattr(annotation, '__origin__', None)
        args = getattr(annotation, '__args__', ())
        
        # Handle Optional[T] / Union[T, None]
        if str(annotation).startswith('typing.Union') or str(annotation).startswith('typing.Optional'):
            if args:
                # Get first non-None type
                for arg in args:
                    if arg is not type(None):
                        return self.__normalize_type_annotation(arg)
        
        # For List[T], Set[T], etc., extract T
        if origin in (list, set, tuple, dict):
            if args:
                return self.__normalize_type_annotation(args[0])
            return origin
        
        return None
    
    def __normalize_type_annotation(self, annotation):
        """
        Convert a type annotation to a callable parser function.
        
        Args:
            annotation: The type annotation from function signature
            
        Returns:
            A callable that can parse string input to the desired type
            
        Raises:
            ValueError: If annotation cannot be converted to a parser
        """
        # Handle missing annotation
        if annotation == inspect.Parameter.empty:
            return str  # default to string
        
        # Handle None
        if annotation is None:
            return str
        
        # Handle string annotations (forward references)
        if isinstance(annotation, str):
            annotation = self.__resolve_string_annotation(annotation)
        
        # Handle typing module types
        if HAS_TYPING_INSPECT:
            result = self.__normalize_typing_with_inspect(annotation)
            if result is not None:
                return result
        elif hasattr(annotation, '__origin__'):
            result = self.__normalize_typing_fallback(annotation)
            if result is not None:
                return result
        
        # Handle AST types
        if annotation in AST_TYPES:
            return ast.literal_eval
        
        # Verify it's callable
        if not callable(annotation):
            raise ValueError(f"Type annotation {annotation} is not callable")
        
        return annotation

    def __is_collection_type(self, annotation):
        """
        Check if annotation is a collection type (list, set, tuple).

        Supported: list[T], List[T], set[T], Set[T], tuple[T, ...], Optional[List[T]].
        Limitations: Nested generics (e.g. List[List[int]]) are treated as
        list of inner type; Tuple[int, str, bool] uses first type only.

        Returns:
            tuple: (is_collection, origin_type, element_type) or (False, None, None)
        """
        origin = get_origin(annotation)

        # Handle Optional[T] / Union[T, None] - unwrap and recurse
        if origin is not None:
            try:
                from typing import Union
                if origin is Union:
                    args = get_args(annotation)
                    if args:
                        # Get first non-None type and recurse
                        non_none_args = [arg for arg in args if arg is not type(None)]
                        if non_none_args:
                            return self.__is_collection_type(non_none_args[0])
            except ImportError:
                pass

        # Handle builtin generics (Python 3.9+): list[str], set[int], etc.
        if isinstance(annotation, GenericAlias):
            origin = annotation.__origin__
            args = getattr(annotation, '__args__', ())
            if origin in (list, set, tuple):
                element_type = args[0] if args else str
                return True, origin, element_type

        # Handle typing module generics: List[str], Set[int], etc.
        if origin is not None and origin in (list, set, tuple):
            args = get_args(annotation)
            element_type = args[0] if args else str
            return True, origin, element_type

        return False, None, None

    def __get_parser_for_type(self, type_annotation):
        """
        Get a parser function for a type annotation.

        Handles Optional[T]/Union[T, None] by extracting T. Complex unions
        (Union[int, str]) use the first type only.

        Args:
            type_annotation: The type to create a parser for

        Returns:
            A callable that can parse string input
        """
        # Handle missing annotation
        if type_annotation == inspect.Parameter.empty:
            return str

        # Handle AST-evaluable types
        if type_annotation in AST_TYPES:
            return ast.literal_eval

        # Handle typing module Optional/Union
        origin = get_origin(type_annotation)
        if origin is not None:
            args = get_args(type_annotation)
            if args:
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    return self.__get_parser_for_type(non_none_args[0])

        # Delegate to full normalization (string annotations, etc.)
        return self.__normalize_type_annotation(type_annotation)
    
    def __setup_collection_type(self, signature, element_type):
        """Setup parser for collection types (list, set, tuple)."""
        try:
            self.parser = self.__get_parser_for_type(element_type)
        except ValueError as e:
            raise ValueError(f"Invalid type annotation for parameter '{self.name}': {e}")
        self.action = "append"
        self.nargs = "+"
        self.required = signature.default == inspect.Parameter.empty
    
    def __setup_boolean_type(self, signature, normalized_type):
        """Setup parser for boolean types."""
        self.parser = None
        self.required = False
        
        if self.name.startswith("no_"):
            self.action = "store_false"
            if self.desc != STR_UNDOCUMENTED and signature.default is True:
                base_name = self.name[3:]
                self.desc = f"Explicitly disable {base_name.replace('_', ' ')}"
        else:
            self.action = "store_true"
            if signature.default is True:
                self.desc = f"{self.desc} [enabled by default]"
            elif signature.default is False:
                self.desc = f"{self.desc} [disabled by default]"
    
    def __setup_regular_type(self, signature):
        """Setup parser for regular (non-collection, non-boolean) types."""
        try:
            self.parser = self.__get_parser_for_type(self.type)
        except ValueError as e:
            raise ValueError(f"Invalid type annotation for parameter '{self.name}': {e}")
        self.action = "store"
        self.required = signature.default == inspect.Parameter.empty
        if signature.default != inspect.Parameter.empty:
            self.desc += f' [default: "{signature.default}"]'
    
    def __init__(self, signature, desc):
        self.name = signature.name
        self.type = signature.annotation
        self.desc = desc

        # Validate the annotation
        is_valid, error_msg = TypeValidator.is_valid_annotation(self.type)
        if not is_valid:
            raise ValueError(f"Invalid type annotation for parameter '{self.name}': {error_msg}")
        
        # Normalize the annotation
        normalized_type = TypeValidator.normalize_annotation(self.type)

        # Check if it's a collection type (list, set, tuple)
        is_collection, origin, element_type = self.__is_collection_type(self.type)

        if is_collection:
            self.__setup_collection_type(signature, element_type)
        elif TypeValidator.is_bool_type(normalized_type):
            self.__setup_boolean_type(signature, normalized_type)
        else:
            self.__setup_regular_type(signature)
    
    def get_argparse_kwargs(self):
        kwargs = {
            'help': self.desc,
            'required': self.required,
            'dest': self.name,
            'action': self.action,
        }

        if self.action in ("store", "append"):
            kwargs['type'] = self.parser

        if self.action == "append":
            kwargs['nargs'] = self.nargs

        # Explicit disable boolean args should reference their enable flag value instead
        normalized_type = TypeValidator.normalize_annotation(self.type)
        if TypeValidator.is_bool_type(normalized_type) and self.name.startswith("no_"):
            kwargs['dest'] = self.name[3:]

        return kwargs


class MLArgParser:
    """
    Multi-level argument parser for creating CLI applications with subcommands.
    
    Boolean Parameter Conventions:
    ------------------------------
    - Boolean parameters with False defaults create --flag options (store_true)
    - Boolean parameters with True defaults create both:
        * --flag option (enabled by default)
        * --no-flag option (explicit disable)
    - Parameters starting with "no_" are treated as disable flags (store_false)
    - Set auto_disable_flags = False to disable automatic --no-* flag generation
    
    Example:
        def my_command(self, verbose: bool = False, cache: bool = True):
            '''My command'''
            pass
        
        # Creates: --verbose (store_true), --cache (store_true), --no-cache (store_false)
    """
    
    # mapping of command arguments to descriptions (initialized in constructor)
    arg_desc = None
    
    # mapping of lower-case commands to method names and attributes (initialized in __init_commands)
    commands = None
    
    # list for tracking auto-generated short options (initialized in __get_cmd_parser)
    short_options = None
    
    auto_disable_flags = True
    
    # Set to True to make command names case-sensitive
    case_sensitive_commands = False
    
    # Set to True to make command name collisions fatal
    strict_validation = True
    
    def __merge_arg_desc(self):
        """Merge arg_desc from parent with local arg_desc."""
        if self.parent and self.parent.arg_desc:
            combined_arg_desc = dict(self.parent.arg_desc)
        else:
            combined_arg_desc = dict()
        
        # combine any explicity-provided argument descriptions into the ones inherited from the parent
        if self.arg_desc is not None:
            for key, value in self.arg_desc.items():
                combined_arg_desc[key] = value
        
        self.arg_desc = combined_arg_desc
    
    def __init__(self, level=1, parent=None, top=None, noparse=False, strict_types=True):
        # indicate how many command-levels deep we are
        self.level = level
        
        # keep track of our parent command
        self.parent = parent
        
        # keep track of our top-level command
        self.top = top if level > 1 else self
        
        # strict_types: if True, raise exceptions for invalid annotations; if False, skip with warning
        self.strict_types = strict_types
        
        if noparse:
            return
        
        # build a dictionary of all commands
        self.__init_commands()
        
        # merge arg_desc from parent
        self.__merge_arg_desc()
        
        # create our top-level parser
        self.parser = argparse.ArgumentParser(
            description=inspect.getdoc(self),
            usage=(("%s " * level) + "<command> [<args>]") % tuple(sys.argv[0:level]),
            epilog=self.__get_epilog_str(),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        self.parser.add_argument('command', help='Sub-command to run')
        
        # parse only the first argument after the current command
        parsed_args = self.parser.parse_args(sys.argv[level:level + 1])
        parsed_command_raw = parsed_args.command
        parsed_command = self.__normalize_command_name(parsed_command_raw)
        
        # make sure it's a valid command and find the corresponding callable
        command_callable = self.__get_cmd_callable(parsed_command)
        
        # get a dictionary representing the arguments for the command
        callable_args = self.__parse_cmd_args(command_callable)
        
        # invoke the callable for the command with all provided arguments
        command_callable(**callable_args)
    
    def __is_append_action(self, action, key):
        """Check if an action is an append action for the given key."""
        dest_match = getattr(action, 'dest', None) == key
        nargs_match = getattr(action, 'nargs', None) == '+'
        action_match = getattr(action, 'action', None) == 'append'
        class_match = (hasattr(action, '__class__') and
                      action.__class__.__name__.endswith('AppendAction'))
        return dest_match and nargs_match and (action_match or class_match)
    
    def __flatten_list_argument(self, func_args, key, cmd_parser):
        """Flatten nested list arguments for append actions."""
        try:
            action = next(
                filter(lambda x: self.__is_append_action(x, key), cmd_parser._actions)
            )
        except StopIteration:
            return  # Not an append action
        
        if not func_args[key]:
            return
        
        if not isinstance(func_args[key], list):
            type_name = type(func_args[key]).__name__
            print(
                f"Warning: Expected list for argument '{key}', got {type_name}",
                file=sys.stderr
            )
            return
        
        flattened = []
        for item in func_args[key]:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)
        
        func_args[key] = flattened
        if not flattened:
            print(
                f"Warning: Argument '{key}' resulted in empty list after flattening",
                file=sys.stderr
            )
    
    def __parse_cmd_args(self, command_callable):
        # intercept sub-commands
        if isinstance(command_callable, type):
            return {'level': self.level + 1, 'parent': self, 'top': self.top}
        
        # get a parser object for the command function
        cmd_parser = self.__get_cmd_parser(command_callable)
        
        # Parse arguments without stderr hijacking
        try:
            parsed = cmd_parser.parse_args(sys.argv[self.level + 1:])
            func_args = vars(parsed)
        except argparse.ArgumentError as e:
            # Print help and error message
            cmd_parser.print_help()
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(2)
        
        for key in list(func_args.keys()):
            # remove any args that weren't specified
            if func_args[key] is None:
                func_args.pop(key)
                continue

            # Look for append (list/set/tuple) arguments with nargs="+" and flatten nested lists
            self.__flatten_list_argument(func_args, key, cmd_parser)
        
        return func_args
    
    def __generate_command_suggestions(self, parsed_command, available_commands):
        """Generate command suggestions for unrecognized commands."""
        suggestions = []
        normalized_input = parsed_command.replace('-', '_').replace('_', '-')
        
        for cmd in available_commands:
            normalized_cmd = cmd.replace('-', '_').replace('_', '-')
            # Check if it's a close match (substring, prefix, etc.)
            if (parsed_command in cmd or cmd in parsed_command or
                normalized_input == normalized_cmd or
                parsed_command.replace('-', '_') == cmd.replace('-', '_') or
                parsed_command.replace('_', '-') == cmd.replace('_', '-')):
                suggestions.append(cmd)
        
        return suggestions
    
    def __get_cmd_callable(self, parsed_command):
        if parsed_command.startswith("_") or parsed_command not in list(self.commands.keys()):
            # Try to find similar commands for helpful error message
            available_commands = list(self.commands.keys())
            suggestions = self.__generate_command_suggestions(parsed_command, available_commands)
            
            error_msg = f"Unrecognized command: {parsed_command}"
            if suggestions:
                suggestions_list = "\n  ".join(suggestions)
                error_msg += f"\n\nDid you mean one of these?\n  {suggestions_list}"
            
            print(error_msg)
            self.parser.print_help()
            sys.exit(1)
        
        # create a parser for the command
        return self.commands[parsed_command][1]
    
    def __normalize_command_name(self, name):
        """
        Normalize command name by replacing underscores with dashes.
        
        Args:
            name: The method name to normalize
            
        Returns:
            Normalized command name (lowercased if case_sensitive_commands is False)
        """
        normalized = name.replace('_', '-')
        if self.case_sensitive_commands:
            return normalized
        else:
            return normalized.lower()
    
    def __validate_command_signature(self, attr, attr_name):
        """Validate a command's signature and return list of errors."""
        command_errors = []
        try:
            sig = inspect.signature(attr)
            self.__validate_boolean_params(sig, attr_name)
            
            for param_name, param in sig.parameters.items():
                is_valid, error_msg = TypeValidator.is_valid_annotation(param.annotation)
                if not is_valid:
                    command_errors.append(
                        f"Command '{attr_name}', parameter '{param_name}': {error_msg}"
                    )
            
            # Also validate by creating CmdArg (catches other issues)
            for param in sig.parameters.values():
                try:
                    param_desc = (self.arg_desc.get(param.name, STR_UNDOCUMENTED)
                                 if self.arg_desc else STR_UNDOCUMENTED)
                    CmdArg(param, param_desc)
                except ValueError as e:
                    command_errors.append(
                        f"Command '{attr_name}', parameter '{param.name}': {e}"
                    )
        except Exception as e:
            command_errors.append(
                f"Command '{attr_name}': Failed to inspect signature: {e}"
            )
        
        return command_errors
    
    def __record_command_collision(self, collisions, cmd_key, attr_name):
        """Record a command name collision."""
        if cmd_key not in collisions:
            collisions[cmd_key] = [self.commands[cmd_key][0]]
        collisions[cmd_key].append(attr_name)
    
    def __report_collisions(self, collisions):
        """Report command name collisions."""
        if not collisions:
            return
        
        error_lines = ["Command name collisions detected:"]
        for cmd_name, method_names in collisions.items():
            error_lines.append(
                f"  Command '{cmd_name}' maps to multiple methods: {', '.join(method_names)}"
            )
            error_lines.append(
                f"    Only '{method_names[-1]}' will be accessible."
            )
        
        error_report = "\n".join(error_lines)
        print(error_report, file=sys.stderr)
        
        # Optionally make this fatal
        if self.strict_validation:
            raise ValueError(error_report)
    
    def __report_validation_errors(self, errors):
        """Report type validation errors."""
        if not errors:
            return
        
        if self.strict_types:
            error_report = "\n  - ".join(["Type validation errors:"] + errors)
        else:
            error_report = "\n  - ".join(["Warning: Type validation errors:"] + errors)
        print(error_report, file=sys.stderr)
        
        # Optionally make this fatal
        # strict_types controls whether type validation errors are fatal
        if self.strict_types:
            raise ValueError(error_report)
    
    def __init_commands(self):
        if self.commands:
            return
        
        self.commands = dict()
        errors = []
        collisions = {}  # Track collisions: normalized_name -> [method_names]
        
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            
            if callable(attr) and not attr_name.startswith("_"):
                # Validate command signatures
                if not isinstance(attr, type):
                    command_errors = self.__validate_command_signature(attr, attr_name)
                    
                    # If there are errors for this command, add to errors list and skip adding command
                    if command_errors:
                        errors.extend(command_errors)
                        # Skip adding this command if strict_types is True, or if we want to skip invalid commands
                        if self.strict_types:
                            continue
                        # In non-strict mode, we still skip commands with validation errors to avoid crashes later
                        continue
                
                # Normalize command name
                cmd_key = self.__normalize_command_name(attr_name)
                
                # Check for collision
                if cmd_key in self.commands:
                    self.__record_command_collision(collisions, cmd_key, attr_name)
                
                # Store the command (will overwrite if collision)
                self.commands[cmd_key] = (attr_name, attr)
        
        # Report collisions and errors
        self.__report_collisions(collisions)
        self.__report_validation_errors(errors)
    
    def __validate_boolean_params(self, signature, command_name):
        """Validate boolean parameter naming to avoid conflicts."""
        param_names = list(signature.parameters.keys())
        
        for param_name in param_names:
            param = signature.parameters[param_name]
            normalized_type = TypeValidator.normalize_annotation(param.annotation)
            
            if TypeValidator.is_bool_type(normalized_type):
                if param_name.startswith("no_no_"):
                    raise ValueError(
                        f"Parameter '{param_name}' uses double negative 'no_no_' prefix. "
                        f"Consider renaming to avoid confusion."
                    )
                
                if param_name.startswith("no_"):
                    base_name = param_name[3:]
                    if base_name in param_names:
                        raise ValueError(
                            f"Both '{base_name}' and '{param_name}' parameters exist. "
                            f"This creates ambiguous flag behavior. Use only one."
                        )
    
    def __get_epilog_str(self):
        # start with a header
        epilog = "available commands:\n"
        
        # retrieve a list of attributes in the current class (excluding dunders)
        cmd_list = list()
        
        # build a list of all commands with descriptions
        for cmd_name, attr in self.commands.values():
            desc = inspect.getdoc(attr)
            
            if not desc:
                desc = STR_UNDOCUMENTED
            
            cmd_list.append([cmd_name, desc])
        
        # determine the max width for the commands column
        if len(cmd_list):
            col_width = max(len(x[0]) for x in cmd_list) + 6
            
            # format each command row
            for row in cmd_list:
                epilog += "  %s\n" % "".join(word.ljust(col_width) for word in row)
        
        return epilog + " "
    
    def __get_options_for_arg(self, arg):
        # initialize short options tracker
        if not self.short_options:
            self.short_options = list()
        
        # underscores in argument names are uncool, so replace them with dashes
        long_option = "--%s" % arg.replace("_", "-")
        
        # try to define a short option if it's not already used
        short_option = "-%s" % arg[0]
        
        if short_option not in self.short_options:
            self.short_options.append(short_option)
            return long_option, short_option
        else:
            return long_option,
    
    def __get_arg_properties(self, command_callable):
        """
        Iterate through parameters and yield CmdArg objects.
        
        For boolean parameters with True defaults, automatically creates
        a corresponding --no-* flag for explicit disabling.
        """
        sig = inspect.signature(command_callable)
        param_names = set(sig.parameters.keys())
        
        for arg in sig.parameters.values():
            if self.arg_desc is None or arg.name not in self.arg_desc:
                desc = STR_UNDOCUMENTED
            else:
                desc = self.arg_desc[arg.name]
            
            yield CmdArg(arg, desc), arg.default
            
            normalized_type = TypeValidator.normalize_annotation(arg.annotation)
            is_bool_with_true_default = (
                self.auto_disable_flags and
                TypeValidator.is_bool_type(normalized_type) and
                arg.default is True
            )
            if is_bool_with_true_default:
                no_name = f"no_{arg.name}"
                
                if no_name in param_names:
                    print(
                        f"Warning: Skipping auto-generation of '--{no_name.replace('_', '-')}' "
                        f"flag because parameter '{no_name}' is explicitly defined.",
                        file=sys.stderr
                    )
                    continue
                
                # Don't create no_no_* flags (double negatives)
                if arg.name.startswith("no_"):
                    continue
                
                yield CmdArg(arg.replace(name=no_name), desc), None
    
    def __get_cmd_parser(self, command_callable):
        # Offset the level from the one passed to the constructor (to skip parsing the previous command)
        level = self.level + 1
        
        # create a parser for the command and a group to track required args
        # Build usage string safely - ensure we have enough argv elements
        argv_slice = sys.argv[0:level] if len(sys.argv) >= level else sys.argv
        usage_str = (("%s " * len(argv_slice)) + "[<args>]") % tuple(argv_slice)
        parser = argparse.ArgumentParser(
            description=inspect.getdoc(command_callable),
            usage=usage_str,
            exit_on_error=False  # New in Python 3.9
        )
        req_args_group = parser.add_argument_group("required arguments")
        defaults = dict()
        
        # populate the parser with the arg and type information from the function
        for arg, default_val in self.__get_arg_properties(command_callable):
            # determine the long and/or short option names for the argument
            options = self.__get_options_for_arg(arg.name)
            
            # get the argparse-compatible keyword list for the argument
            kwargs = arg.get_argparse_kwargs()
            
            # determine which group to place an argument in based on whether or not it's required
            grp = req_args_group if arg.required else parser
            
            # add the argument to the appropriate group
            grp.add_argument(*options, **kwargs)

            # build a list of default args for the parser object
            if default_val not in (None, inspect.Parameter.empty):
                defaults[arg.name] = default_val

        # set default values
        parser.set_defaults(**defaults)
        
        return parser

