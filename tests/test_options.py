#!/usr/bin/env python3
"""Tests for short and long option handling."""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser


class TestLongOptions(unittest.TestCase):
    """Test long option (--option) generation."""

    def test_long_option_from_underscore(self):
        """Test that underscores become dashes in long options."""
        class App(MLArgParser):
            def cmd(self, my_option: str):
                self.result = my_option

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        self.assertIn('--my-option', option_strings)

    def test_long_option_always_created(self):
        """Test that long option is always created."""
        class App(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        self.assertIn('--value', option_strings)


class TestShortOptions(unittest.TestCase):
    """Test short option (-o) generation."""

    def test_short_option_created(self):
        """Test that short option is created when available."""
        class App(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        self.assertIn('-v', option_strings)

    def test_short_option_collision(self):
        """Test that short option collision is handled."""
        class App(MLArgParser):
            def cmd(self, value: str, verbose: bool = False):
                self.result = (value, verbose)

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        # Both value and verbose start with 'v'
        # First one should get -v, second should only have long option
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        
        # value should have -v
        value_action = next(a for a in parser._actions if a.dest == 'value')
        self.assertIn('-v', value_action.option_strings)
        
        # verbose should NOT have -v (collision)
        verbose_action = next(a for a in parser._actions if a.dest == 'verbose')
        self.assertNotIn('-v', verbose_action.option_strings)

    def test_short_option_uses_first_letter(self):
        """Test that short option uses first letter of argument name."""
        class App(MLArgParser):
            def cmd(self, alpha: str, beta: str):
                self.result = (alpha, beta)

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        alpha_action = next(a for a in parser._actions if a.dest == 'alpha')
        self.assertIn('-a', alpha_action.option_strings)
        
        beta_action = next(a for a in parser._actions if a.dest == 'beta')
        self.assertIn('-b', beta_action.option_strings)


class TestOptionUsage(unittest.TestCase):
    """Test actual usage of short and long options."""

    def test_long_option_works(self):
        """Test that long option can be used."""
        class App(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', 'test']):
            app = App()
            self.assertEqual(app.result, "test")

    def test_short_option_works(self):
        """Test that short option can be used."""
        class App(MLArgParser):
            def cmd(self, value: str):
                self.result = value

        with patch.object(sys, 'argv', ['prog', 'cmd', '-v', 'test']):
            app = App()
            self.assertEqual(app.result, "test")

    def test_mixed_options(self):
        """Test mixing short and long options."""
        class App(MLArgParser):
            def cmd(self, value: str, count: int):
                self.result = (value, count)

        with patch.object(sys, 'argv', ['prog', 'cmd', '-v', 'test', '--count', '42']):
            app = App()
            self.assertEqual(app.result, ("test", 42))


if __name__ == '__main__':
    unittest.main()
