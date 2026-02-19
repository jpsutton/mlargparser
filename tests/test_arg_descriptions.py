#!/usr/bin/env python3
"""Tests for argument description handling."""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser, STR_UNDOCUMENTED


class TestArgDesc(unittest.TestCase):
    """Test arg_desc dictionary functionality."""

    def test_arg_desc_provides_description(self):
        """Test that arg_desc provides argument descriptions."""
        class App(MLArgParser):
            arg_desc = {
                "value": "A test value for the command"
            }

            def cmd(self, value: str):
                self.result = value

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        value_action = next(a for a in parser._actions if a.dest == 'value')
        self.assertEqual(value_action.help, "A test value for the command")

    def test_missing_arg_desc_uses_undocumented(self):
        """Test that missing arg_desc uses STR_UNDOCUMENTED."""
        class App(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        value_action = next(a for a in parser._actions if a.dest == 'value')
        self.assertEqual(value_action.help, STR_UNDOCUMENTED)

    def test_arg_desc_inheritance(self):
        """Test that subcommands inherit arg_desc from parent."""
        class SubApp(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        class App(MLArgParser):
            arg_desc = {"value": "Inherited description"}

            def sub(self):
                return SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)
        sub_app._MLArgParser__init_commands()
        sub_app._MLArgParser__merge_arg_desc()
        
        self.assertIn("value", sub_app.arg_desc)
        self.assertEqual(sub_app.arg_desc["value"], "Inherited description")

    def test_arg_desc_override(self):
        """Test that local arg_desc overrides parent."""
        class SubApp(MLArgParser):
            arg_desc = {"value": "Local description"}

            def cmd(self, value: str):
                self.result = value

        class App(MLArgParser):
            arg_desc = {"value": "Parent description"}

            def sub(self):
                return SubApp

        app = App(noparse=True)
        sub_app = SubApp(level=2, parent=app, top=app, noparse=True)
        sub_app._MLArgParser__init_commands()
        sub_app._MLArgParser__merge_arg_desc()
        
        # Local should override parent
        self.assertEqual(sub_app.arg_desc["value"], "Local description")

    def test_arg_desc_validation(self):
        """Test validation of arg_desc keys."""
        import io
        from contextlib import redirect_stderr

        class App(MLArgParser):
            arg_desc = {
                "valid_arg": "Valid argument",
                "invalid_arg": "This doesn't exist in signature"
            }

            def cmd(self, valid_arg: str):
                self.result = valid_arg

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__validate_argdesc(app.cmd)
        
        output = stderr.getvalue()
        self.assertIn("invalid_arg", output)
        self.assertIn("Warning", output)


class TestDefaultValueInDescription(unittest.TestCase):
    """Test that default values appear in descriptions."""

    def test_default_value_in_description(self):
        """Test that default value is included in description."""
        class App(MLArgParser):
            def cmd(self, value: str = "default"):
                self.result = value

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        value_action = next(a for a in parser._actions if a.dest == 'value')
        self.assertIn("default", value_action.help)
        self.assertIn('"default"', value_action.help)


if __name__ == '__main__':
    unittest.main()
