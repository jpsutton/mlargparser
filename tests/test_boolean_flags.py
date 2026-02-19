#!/usr/bin/env python3
"""Comprehensive tests for boolean flag handling."""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser


class TestBooleanFlagDefaults(unittest.TestCase):
    """Test boolean flags with different default values."""

    def test_false_default_store_true(self):
        """Boolean with False default creates store_true action."""
        class App(MLArgParser):
            def cmd(self, verbose: bool = False):
                self.result = verbose

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertFalse(app.result)

        with patch.object(sys, 'argv', ['prog', 'cmd', '--verbose']):
            app = App()
            self.assertTrue(app.result)

    def test_true_default_store_true(self):
        """Boolean with True default creates store_true action."""
        class App(MLArgParser):
            def cmd(self, cache: bool = True):
                self.result = cache

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertTrue(app.result)

        with patch.object(sys, 'argv', ['prog', 'cmd', '--cache']):
            app = App()
            self.assertTrue(app.result)

    def test_no_prefix_store_false(self):
        """Parameters starting with 'no_' create store_false action."""
        from mlargparser import CmdArg
        import inspect

        param = inspect.Parameter('no_cache', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                 default=False, annotation=bool)
        arg = CmdArg(param, "Disable cache")
        
        self.assertEqual(arg.action, 'store_false')
        # Check that dest is set correctly (strips no_ prefix)
        kwargs = arg.get_argparse_kwargs()
        self.assertEqual(kwargs['dest'], 'cache')


class TestAutoDisableFlags(unittest.TestCase):
    """Test automatic --no-* flag generation."""

    def test_auto_generate_no_flag_for_true_default(self):
        """Auto-generate --no-* flag for bool=True defaults."""
        class App(MLArgParser):
            def cmd(self, cache: bool = True):
                self.result = cache

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        # Should have both --cache and --no-cache
        actions = {action.dest: action for action in parser._actions}
        self.assertIn('cache', actions)
        self.assertIn('cache', [a.dest for a in parser._actions if '--no-cache' in str(a.option_strings)])

    def test_no_auto_generate_when_disabled(self):
        """Don't auto-generate when auto_disable_flags=False."""
        class App(MLArgParser):
            auto_disable_flags = False

            def cmd(self, cache: bool = True):
                self.result = cache

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        # Should only have --cache, not --no-cache
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        self.assertIn('--cache', option_strings)
        self.assertNotIn('--no-cache', option_strings)

    def test_no_auto_generate_if_explicitly_defined(self):
        """Defining both cache and no_cache explicitly should raise an error."""
        class App(MLArgParser):
            def cmd(self, cache: bool = True, no_cache: bool = False):
                self.result = (cache, no_cache)

        app = App(noparse=True, strict_types=True)
        
        # Should raise ValueError because both cache and no_cache are defined
        # This creates ambiguous flag behavior
        with self.assertRaises(ValueError) as ctx:
            app._MLArgParser__init_commands()
        
        error_msg = str(ctx.exception)
        self.assertIn("cache", error_msg)
        self.assertIn("no_cache", error_msg)
        self.assertIn("ambiguous", error_msg.lower())

    def test_no_auto_generate_for_no_prefix_params(self):
        """Don't auto-generate --no-no-* flags (double negative)."""
        class App(MLArgParser):
            def cmd(self, no_cache: bool = False):
                self.result = no_cache

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        parser = app._MLArgParser__get_cmd_parser(app.cmd)
        
        # Should not have --no-no-cache
        option_strings = [opt for action in parser._actions for opt in action.option_strings]
        self.assertNotIn('--no-no-cache', option_strings)


class TestBooleanFlagBehavior(unittest.TestCase):
    """Test actual behavior of boolean flags."""

    def test_store_true_flag_sets_true(self):
        """--flag sets boolean to True."""
        class App(MLArgParser):
            def cmd(self, verbose: bool = False):
                self.result = verbose

        with patch.object(sys, 'argv', ['prog', 'cmd', '--verbose']):
            app = App()
            self.assertTrue(app.result)

    def test_no_flag_sets_false(self):
        """--no-flag sets boolean to False."""
        class App(MLArgParser):
            def cmd(self, cache: bool = True):
                self.result = cache

        with patch.object(sys, 'argv', ['prog', 'cmd', '--no-cache']):
            app = App()
            self.assertFalse(app.result)

    def test_mixed_boolean_flags(self):
        """Test command with multiple boolean flags."""
        class App(MLArgParser):
            def cmd(self, verbose: bool = False, cache: bool = True):
                self.result = (verbose, cache)

        with patch.object(sys, 'argv', ['prog', 'cmd', '--verbose', '--no-cache']):
            app = App()
            self.assertEqual(app.result, (True, False))

    def test_boolean_without_flag_uses_default(self):
        """Boolean without flag uses default value."""
        class App(MLArgParser):
            def cmd(self, verbose: bool = False, cache: bool = True):
                self.result = (verbose, cache)

        with patch.object(sys, 'argv', ['prog', 'cmd']):
            app = App()
            self.assertEqual(app.result, (False, True))


class TestBooleanFlagDescriptions(unittest.TestCase):
    """Test description text for boolean flags."""

    def test_false_default_description(self):
        """Boolean with False default shows '[disabled by default]'."""
        from mlargparser import CmdArg
        import inspect

        param = inspect.Parameter('verbose', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                 default=False, annotation=bool)
        arg = CmdArg(param, "Enable verbose output")
        self.assertIn("[disabled by default]", arg.desc)

    def test_true_default_description(self):
        """Boolean with True default shows '[enabled by default]'."""
        from mlargparser import CmdArg
        import inspect

        param = inspect.Parameter('cache', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                 default=True, annotation=bool)
        arg = CmdArg(param, "Use caching")
        self.assertIn("[enabled by default]", arg.desc)

    def test_no_prefix_description(self):
        """no_ prefix parameters get special description."""
        from mlargparser import CmdArg, STR_UNDOCUMENTED
        import inspect

        param = inspect.Parameter('no_cache', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                 default=True, annotation=bool)
        arg = CmdArg(param, "Disable caching")
        if arg.desc != STR_UNDOCUMENTED:
            self.assertIn("disable", arg.desc.lower())


if __name__ == '__main__':
    unittest.main()
