#!/usr/bin/env python3
"""Tests for subcommand functionality.

Subcommands are implemented as command trees: you assign a subclass of
MLArgParser as a class attribute. For example:

    class DumpCmd(MLArgParser):
        def config(self): ...
        def state(self): ...
        def authtoken(self): ...

    class MyApp(MLArgParser):
        dump = DumpCmd   # subcommand: ./app.py dump config|state|authtoken

When the user runs ./app.py dump config, the top-level parser selects "dump",
gets DumpCmd (the class), and instantiates it with level=2, parent=app, top=app.
That sub-parser then parses "config" and dispatches to DumpCmd.config().
"""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser


class TestSubcommandTreePattern(unittest.TestCase):
    """Test the class-attribute subcommand pattern: dump = DumpCmd."""

    def test_dump_config_state_authtoken_pattern(self):
        """Test tree of commands: ./app.py dump config|state|authtoken."""
        class DumpCmd(MLArgParser):
            """Dump subcommand: config, state, authtoken."""
            def config(self):
                """Dump config."""
                self.top.result = "config"

            def state(self):
                """Dump state."""
                self.top.result = "state"

            def authtoken(self):
                """Dump authtoken."""
                self.top.result = "authtoken"

        class MyApp(MLArgParser):
            """Top-level app with dump subcommand."""
            dump = DumpCmd

        # Verify subcommand is registered as the class (not a method)
        app = MyApp(noparse=True)
        app._MLArgParser__init_commands()

        self.assertIn("dump", app.commands)
        cmd_name, cmd_callable = app.commands["dump"]
        self.assertEqual(cmd_name, "dump")
        # Subcommand must be the class itself so it can be instantiated
        self.assertIs(cmd_callable, DumpCmd)

        # When "dump" is selected, parse_cmd_args should return subcommand init dict
        sub_args = app._MLArgParser__parse_cmd_args(DumpCmd)
        self.assertEqual(sub_args["level"], 2)
        self.assertEqual(sub_args["parent"], app)
        self.assertEqual(sub_args["top"], app)

        # End-to-end: ./app.py dump config -> DumpCmd runs and dispatches to config()
        # (subcommand sets self.top.result so we can read it from the top-level app)
        with patch.object(sys, "argv", ["prog", "dump", "config"]):
            app = MyApp()
            self.assertEqual(app.result, "config")

        with patch.object(sys, "argv", ["prog", "dump", "state"]):
            app = MyApp()
            self.assertEqual(app.result, "state")

        with patch.object(sys, "argv", ["prog", "dump", "authtoken"]):
            app = MyApp()
            self.assertEqual(app.result, "authtoken")

    def test_subcommand_with_args(self):
        """Subcommand methods can take arguments: ./app.py dump config --format json."""
        class DumpCmd(MLArgParser):
            def config(self, format: str = "text"):
                """Dump config."""
                self.top.result = format

        class MyApp(MLArgParser):
            dump = DumpCmd

        with patch.object(sys, "argv", ["prog", "dump", "config", "--format", "json"]):
            app = MyApp()
            self.assertEqual(app.result, "json")


class TestSubcommandStructure(unittest.TestCase):
    """Test subcommand registration and parsing structure."""

    def test_class_attribute_registered_as_subcommand(self):
        """Assigning a class (dump = DumpCmd) registers it; selecting it returns init dict."""
        class DumpCmd(MLArgParser):
            def config(self):
                pass

        class MyApp(MLArgParser):
            dump = DumpCmd

        app = MyApp(noparse=True)
        app._MLArgParser__init_commands()

        self.assertIn("dump", app.commands)
        self.assertIs(app.commands["dump"][1], DumpCmd)

        # Parsing "dump" as subcommand yields init kwargs for the sub-parser
        sub_args = app._MLArgParser__parse_cmd_args(DumpCmd)
        self.assertEqual(sub_args["level"], 2)
        self.assertIs(sub_args["parent"], app)
        self.assertIs(sub_args["top"], app)

    def test_subcommand_inherits_arg_desc(self):
        """Subcommand parser inherits arg_desc from parent when instantiated."""
        class SubApp(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        class App(MLArgParser):
            arg_desc = {"value": "A test value"}
            sub = SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)
        sub_app._MLArgParser__init_commands()
        sub_app._MLArgParser__merge_arg_desc()

        self.assertIsNotNone(sub_app.arg_desc)
        self.assertIn("value", sub_app.arg_desc)

    def test_subcommand_level_tracking(self):
        """Subcommand instance has correct level, parent, top."""
        class SubApp(MLArgParser):
            def cmd(self, value: str):
                pass

        class App(MLArgParser):
            sub = SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)

        self.assertEqual(sub_app.level, 2)
        self.assertIs(sub_app.parent, app)
        self.assertIs(sub_app.top, app)

    def test_nested_subcommands(self):
        """Three-level tree: app -> sub -> subsub."""
        class SubSubApp(MLArgParser):
            def action(self, value: str):
                self.result = value

        class SubApp(MLArgParser):
            subsub = SubSubApp

        class App(MLArgParser):
            sub = SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)
        sub_sub_app = SubSubApp(level=3, parent=sub_app, top=app, noparse=True)

        self.assertEqual(sub_sub_app.level, 3)
        self.assertIs(sub_sub_app.top, app)


class TestSubcommandParsing(unittest.TestCase):
    """Test that subcommand parsers and their args work."""

    def test_subcommand_parses_own_args(self):
        """Subcommand command methods get their own argument parser."""
        class SubApp(MLArgParser):
            def cmd(self, arg1: str, arg2: int = 10):
                self.result = (arg1, arg2)

        class App(MLArgParser):
            sub = SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)
        sub_app._MLArgParser__init_commands()

        parser = sub_app._MLArgParser__get_cmd_parser(sub_app.cmd)
        self.assertIsNotNone(parser)


if __name__ == '__main__':
    unittest.main()
