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

# string to use for undocumented commands/arguments
STR_UNDOCUMENTED = "FIXME: UNDOCUMENTED"

# list of types that can be safely converted from string by the ast.literal_eval method
AST_TYPES = [list, tuple, dict, set]

# Set this environment variable to help the argparse formatter wrap the lines
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)


class CmdArg:
    name = ""
    desc = ""
    type = None
    required = False
    action = ""
    nargs = 1
    
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
            # Try to evaluate in common namespaces
            try:
                import builtins
                annotation = getattr(builtins, annotation)
            except AttributeError:
                raise ValueError(f"Cannot resolve string annotation: {annotation}")
        
        # Handle typing module types
        # Use typing inspection utilities if available (Python 3.8+)
        if HAS_TYPING_INSPECT:
            origin = get_origin(annotation)
            if origin is not None:
                args = get_args(annotation)
                # Handle Optional[T] / Union[T, None]
                # Optional[T] is equivalent to Union[T, None]
                try:
                    from typing import Union
                    if origin is Union:
                        if args:
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
        elif hasattr(annotation, '__origin__'):
            # Fallback for older Python versions or typing module without get_origin
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
        
        # Handle AST types
        if annotation in AST_TYPES:
            return ast.literal_eval
        
        # Verify it's callable
        if not callable(annotation):
            raise ValueError(f"Type annotation {annotation} is not callable")
        
        return annotation
    
    def __init__(self, signature, desc):
        self.name = signature.name
        self.type = signature.annotation
        
        try:
            self.parser = self.__normalize_type_annotation(self.type)
        except ValueError as e:
            # Provide helpful error message with parameter name
            raise ValueError(f"Invalid type annotation for parameter '{self.name}': {e}")
        
        self.desc = desc
        self.required = False if self.type == bool else (signature.default == inspect.Parameter.empty)

        # Booleans need special hand-holding
        if self.type == bool:
            if self.name.startswith("no_"):
                self.action = "store_false"

                if self.desc != STR_UNDOCUMENTED and signature.default == True:
                    self.desc = f"Explicitly do not {self.desc[0].lower()}{self.desc[1:]}"
            else:
                self.action = "store_true"

                if signature.default == True:
                    self.desc = f"{self.desc} [default]"
        elif type(self.type) == GenericAlias and type(self.type()) == list:
            self.parser = self.type.__args__[0]
            self.action = "append"
            self.nargs = "+"
        else:
            self.action = "store"

            if signature.default != inspect.Parameter.empty:
                self.desc += f' [default: "{signature.default}"]'
    
    def get_argparse_kwargs(self):
        retval = {
            'help': self.desc,
            'required': self.required,
            'dest': self.name,
            'action': self.action,
        }

        if self.action in ("store", "append"):
            retval['type'] = self.parser

        if self.action == "append":
            retval['nargs'] = self.nargs

        # Explicit disable boolean args should reference their enable flag value instead
        if self.type == bool and self.name.startswith("no_"):
            retval['dest'] = self.name[3:]

        return retval



class MLArgParser:
    __doc__ = STR_UNDOCUMENTED
    
    # mapping of command arguments to descriptions (initialized in constructor)
    argDesc = None
    
    # mapping of lower-case commands to method names and attributes (initialized in __init_commands)
    commands = None
    
    # list for tracking auto-generated short options (initialized in __get_cmd_parser)
    short_options = None
    
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
        
        # try to inherit the argDesc dictionary from the parent
        if self.parent and self.parent.argDesc:
            combinedArgDesc = dict(self.parent.argDesc)
        else:
            combinedArgDesc = dict()
        
        # combine any explicity-provided argument descriptions into the ones inherited from the parent
        if self.argDesc is not None:
            for key, value in self.argDesc.items():
                combinedArgDesc[key] = value
        
        self.argDesc = combinedArgDesc
        
        # create our top-level parser
        self.parser = argparse.ArgumentParser(
            description=inspect.getdoc(self),
            usage=(("%s " * level) + "<command> [<args>]") % tuple(sys.argv[0:level]),
            epilog=self.__get_epilog_str(),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        self.parser.add_argument('command', help='Sub-command to run')
        
        # parse only the first argument after the current command
        parsed_command = self.parser.parse_args(sys.argv[level:level + 1]).command.lower()
        
        # make sure it's a valid command and find the corresponding callable
        command_callable = self.__get_cmd_callable(parsed_command)
        
        # get a dictionary representing the arguments for the command
        callable_args = self.__parse_cmd_args(command_callable)
        
        # invoke the callable for the command with all provided arguments
        command_callable(**callable_args)
    
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

            # Look for any list-based arguments, and flatten them
            try:
                action = next(
                    filter(lambda x: getattr(x, 'dest') == key and getattr(x, 'nargs') == "+", cmd_parser._actions)
                )
                if len(func_args[key]):
                    func_args[key] = [x[0] for x in func_args[key]]
            except StopIteration:
                pass
        
        return func_args
    
    def __get_cmd_callable(self, parsed_command):
        if parsed_command.startswith("_") or parsed_command not in list(self.commands.keys()):
            print(('Unrecognized command: %s' % parsed_command))
            self.parser.print_help()
            exit(1)
        
        # create a parser for the command
        return self.commands[parsed_command][1]
    
    def __init_commands(self):
        if self.commands:
            return
        
        self.commands = dict()
        
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            
            if callable(attr) and not attr_name.startswith("_"):
                # Validate command signatures early
                if not isinstance(attr, type):  # Skip subcommand classes
                    try:
                        sig = inspect.signature(attr)
                        for param in sig.parameters.values():
                            # This will raise ValueError if annotation is invalid
                            CmdArg(param, self.argDesc.get(param.name, STR_UNDOCUMENTED) if self.argDesc else STR_UNDOCUMENTED)
                    except ValueError as e:
                        if self.strict_types:
                            raise
                        print(f"Warning: Skipping command '{attr_name}': {e}", file=sys.stderr)
                        continue
                
                self.commands[attr_name.lower()] = (attr_name, attr)
    
    def __get_epilog_str(self):
        # start with a header
        epilog = "available commands:\n"
        
        # retrieve a list of attributes in the current class (excluding dunders)
        cmd_list = list()
        
        # build a list of all commands with descriptions
        for (cmd_name, attr) in self.commands.values():
            desc = inspect.getdoc(attr)
            
            if not desc:
                desc = STR_UNDOCUMENTED
            
            cmd_list.append([cmd_name, desc])
        
        # determine the max width for the commands column
        if len(cmd_list):
            col_width = max(len(cmd) for cmd in list([x[0] for x in cmd_list])) + 6
            
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
        # Iterate through each parameter in the callable's signature
        for arg in inspect.signature(command_callable).parameters.values():
            # Determine if we have a description for the parameter, if not use the default text
            if self.argDesc is None or arg.name not in self.argDesc:
                desc = STR_UNDOCUMENTED
            else:
                desc = self.argDesc[arg.name]
            
            # Yield an argument object back to the caller
            yield CmdArg(arg, desc), arg.default

            # If a boolean flag is set to True by default, create a corresponding explicit disable flag
            if arg.annotation == bool and arg.default == True:
                yield CmdArg(arg.replace(name = f"no_{arg.name}"), desc), None
    
    def __get_cmd_parser(self, command_callable):
        # Offset the level from the one passed to the constructor (to skip parsing the previous command)
        level = self.level + 1
        
        # create a parser for the command and a group to track required args
        parser = argparse.ArgumentParser(
            description=inspect.getdoc(command_callable),
            usage=(("%s " * level) + "[<args>]") % tuple(sys.argv[0:level]),
            exit_on_error=False  # New in Python 3.9
        )
        req_args_grp = parser.add_argument_group("required arguments")
        defaults = dict()
        
        # populate the parser with the arg and type information from the function
        for arg, default_val in self.__get_arg_properties(command_callable):
            # determine the long and/or short option names for the argument
            options = self.__get_options_for_arg(arg.name)
            
            # get the argparse-compatible keyword list for the argument
            kwargs = arg.get_argparse_kwargs()
            
            # determine which group to place an argument in based on whether or not it's required
            grp = req_args_grp if arg.required else parser
            
            # add the argument to the appropriate group
            grp.add_argument(*options, **kwargs)

            # build a list of default args for the parser object
            if default_val not in (None, inspect._empty):
                defaults[arg.name] = default_val

        # set default values
        parser.set_defaults(**defaults)
        
        return parser

