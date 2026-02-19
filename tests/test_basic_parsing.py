#!/usr/bin/env python3
"""Tests for basic command parsing functionality."""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser


class TestBasicCommandParsing(unittest.TestCase):
    """Test basic command parsing and execution."""

    def test_simple_command(self):
        """Test a simple command with required arguments."""
        class App(MLArgParser):
            def hello(self, name: str):
                """Say hello to someone."""
                self.result = f"Hello, {name}!"

        with patch.object(sys, 'argv', ['prog', 'hello', '--name', 'World']):
            app = App()
            self.assertEqual(app.result, "Hello, World!")

    def test_command_with_optional_args(self):
        """Test command with optional arguments."""
        class App(MLArgParser):
            def greet(self, name: str, title: str = "Mr"):
                """Greet someone with optional title."""
                self.result = f"Hello, {title} {name}!"

        with patch.object(sys, 'argv', ['prog', 'greet', '--name', 'Smith']):
            app = App()
            self.assertEqual(app.result, "Hello, Mr Smith!")

        with patch.object(sys, 'argv', ['prog', 'greet', '--name', 'Smith', '--title', 'Dr']):
            app = App()
            self.assertEqual(app.result, "Hello, Dr Smith!")

    def test_multiple_commands(self):
        """Test app with multiple commands."""
        class App(MLArgParser):
            def cmd1(self, arg1: str):
                """First command."""
                self.result = f"cmd1: {arg1}"

            def cmd2(self, arg2: int):
                """Second command."""
                self.result = f"cmd2: {arg2}"

        with patch.object(sys, 'argv', ['prog', 'cmd1', '--arg1', 'test']):
            app = App()
            self.assertEqual(app.result, "cmd1: test")

        with patch.object(sys, 'argv', ['prog', 'cmd2', '--arg2', '42']):
            app = App()
            self.assertEqual(app.result, "cmd2: 42")

    def test_command_with_docstring(self):
        """Test that docstrings are used for help text."""
        class App(MLArgParser):
            def mycmd(self, value: int):
                """This is a test command with a docstring."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.mycmd)
        self.assertIn("This is a test command", parser.description)

    def test_command_without_docstring(self):
        """Test command without docstring uses UNDOCUMENTED."""
        from mlargparser import STR_UNDOCUMENTED

        class App(MLArgParser):
            def mycmd(self, value: int):
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.mycmd)
        # Parser description comes from inspect.getdoc, which returns None for empty docstrings
        # The epilog will show STR_UNDOCUMENTED for commands without docstrings
        epilog = app._MLArgParser__get_epilog_str()
        self.assertIn(STR_UNDOCUMENTED, epilog)


class TestArgumentTypes(unittest.TestCase):
    """Test parsing of different argument types."""

    def test_string_argument(self):
        """Test string argument parsing."""
        class App(MLArgParser):
            def cmd(self, text: str):
                self.result = text

        with patch.object(sys, 'argv', ['prog', 'cmd', '--text', 'hello']):
            app = App()
            self.assertEqual(app.result, "hello")

    def test_integer_argument(self):
        """Test integer argument parsing."""
        class App(MLArgParser):
            def cmd(self, num: int):
                self.result = num

        with patch.object(sys, 'argv', ['prog', 'cmd', '--num', '42']):
            app = App()
            self.assertEqual(app.result, 42)

    def test_float_argument(self):
        """Test float argument parsing."""
        class App(MLArgParser):
            def cmd(self, value: float):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', '3.14']):
            app = App()
            self.assertAlmostEqual(app.result, 3.14)

    def test_no_type_annotation_defaults_to_str(self):
        """Test that missing type annotation defaults to string."""
        class App(MLArgParser):
            def cmd(self, value):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', 'test']):
            app = App()
            self.assertEqual(app.result, "test")

    def test_none_type_annotation_defaults_to_str(self):
        """Test that None type annotation defaults to string."""
        class App(MLArgParser):
            def cmd(self, value: None):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', 'test']):
            app = App()
            self.assertEqual(app.result, "test")


class TestDefaultValues(unittest.TestCase):
    """Test handling of default parameter values."""

    def test_default_string(self):
        """Test string parameter with default value."""
        class App(MLArgParser):
            def cmd(self, name: str = "default"):
                self.result = name

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertEqual(app.result, "default")

        with patch.object(sys, 'argv', ['prog', 'cmd', '--name', 'custom']):
            app = App()
            self.assertEqual(app.result, "custom")

    def test_default_integer(self):
        """Test integer parameter with default value."""
        class App(MLArgParser):
            def cmd(self, count: int = 10):
                self.result = count

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertEqual(app.result, 10)

    def test_required_vs_optional(self):
        """Test required vs optional parameters."""
        class App(MLArgParser):
            def cmd(self, required: str, optional: str = "default"):
                self.result = (required, optional)

        with patch.object(sys, 'argv', ['prog', 'cmd', '--required', 'req']):
            app = App()
            self.assertEqual(app.result, ("req", "default"))

        with patch.object(sys, 'argv', ['prog', 'cmd', '--required', 'req', '--optional', 'opt']):
            app = App()
            self.assertEqual(app.result, ("req", "opt"))


if __name__ == '__main__':
    unittest.main()
