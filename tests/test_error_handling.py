#!/usr/bin/env python3
"""Tests for error handling and edge cases."""

import sys
import unittest
from unittest.mock import patch, MagicMock

from mlargparser import MLArgParser


class TestInvalidCommand(unittest.TestCase):
    """Test handling of invalid/unrecognized commands."""

    def test_unrecognized_command(self):
        """Test error message for unrecognized command."""
        class App(MLArgParser):
            def valid_cmd(self):
                pass

        with patch.object(sys, 'argv', ['prog', 'invalid']):
            # The code calls exit(1), which raises SystemExit
            with self.assertRaises(SystemExit):
                App()

    def test_command_suggestions(self):
        """Test that similar commands are suggested."""
        class App(MLArgParser):
            def deploy(self):
                pass

            def delete(self):
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        
        suggestions = app._MLArgParser__generate_command_suggestions("deplo", list(app.commands.keys()))
        self.assertIn("deploy", suggestions)


class TestInvalidArguments(unittest.TestCase):
    """Test handling of invalid arguments."""

    def test_missing_required_argument(self):
        """Test error when required argument is missing."""
        class App(MLArgParser):
            def cmd(self, required: str):
                self.result = required

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            # The code calls exit(2), which raises SystemExit
            with self.assertRaises(SystemExit):
                App()

    def test_invalid_type_conversion(self):
        """Test error when type conversion fails."""
        class App(MLArgParser):
            def cmd(self, value: int):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', 'not_a_number']):
            # The code calls exit(2), which raises SystemExit
            with self.assertRaises(SystemExit):
                App()


class TestEdgeCases(unittest.TestCase):
    """Test various edge cases."""

    def test_empty_command_list(self):
        """Test app with no commands."""
        class App(MLArgParser):
            pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        self.assertEqual(len(app.commands), 0)

    def test_command_starting_with_underscore(self):
        """Test that commands starting with _ are ignored."""
        class App(MLArgParser):
            def _private(self):
                """Private method."""
                pass

            def public(self):
                """Public command."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        
        self.assertNotIn("_private", app.commands)
        self.assertIn("public", app.commands)

    def test_empty_list_argument(self):
        """Test handling of empty list arguments."""
        class App(MLArgParser):
            def cmd(self, items: list[str] = None):
                self.result = items

        # Empty list handling depends on argparse behavior
        # This test verifies the code doesn't crash
        app = App(noparse=True)
        app._MLArgParser__init_commands()

    def test_none_default_value(self):
        """Test None as default value."""
        class App(MLArgParser):
            def cmd(self, value: str = None):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertIsNone(app.result)

    def test_multiple_optional_args(self):
        """Test command with multiple optional arguments."""
        class App(MLArgParser):
            def cmd(self, a: str = "a", b: str = "b", c: str = "c"):
                self.result = (a, b, c)

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertEqual(app.result, ("a", "b", "c"))

        with patch.object(sys, 'argv', ['prog', 'cmd', '--c', 'C']):
            app = App()
            self.assertEqual(app.result, ("a", "b", "C"))


class TestHelpText(unittest.TestCase):
    """Test help text generation."""

    def test_help_includes_commands(self):
        """Test that help includes available commands."""
        class App(MLArgParser):
            def cmd1(self):
                """First command."""
                pass

            def cmd2(self):
                """Second command."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        epilog = app._MLArgParser__get_epilog_str()
        
        self.assertIn("cmd1", epilog)
        self.assertIn("cmd2", epilog)

    def test_help_includes_descriptions(self):
        """Test that help includes command descriptions."""
        class App(MLArgParser):
            def cmd(self):
                """This is a test command."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        epilog = app._MLArgParser__get_epilog_str()
        
        self.assertIn("This is a test command", epilog)


if __name__ == '__main__':
    unittest.main()
