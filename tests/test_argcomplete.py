#!/usr/bin/env python3
"""Tests for optional argcomplete integration (mlargparser_argcomplete).

These tests assert on the shape of the completion parser built by
build_completion_parser(). They do not require argcomplete to be installed.
"""

import argparse
import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser
import mlargparser_argcomplete


def _get_subparser_choices(parser):
    """Return the dict of subparser name -> parser for a parser that has subparsers."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    return None


class TestBuildCompletionParser(unittest.TestCase):
    """Test build_completion_parser() produces the expected parser structure."""

    def test_flat_commands_subparser_names(self):
        """Root parser has subparsers for each command."""
        class App(MLArgParser):
            """App with two commands."""
            def list_(self, count: int = 10):
                """List items."""
                pass

            def run(self, format: str = "text"):
                """Run task."""
                pass

        with patch.object(sys, "argv", ["prog"]):
            app = App(noparse=True)
            app._MLArgParser__init_commands()
            app._MLArgParser__merge_arg_desc()
            parser = mlargparser_argcomplete.build_completion_parser(app)

        choices = _get_subparser_choices(parser)
        self.assertIsNotNone(choices)
        # list_ normalizes to list- (underscore -> dash)
        self.assertIn("list-", choices)
        self.assertIn("run", choices)
        self.assertEqual(len(choices), 2)

    def test_flat_command_has_options(self):
        """A method subparser has the expected option arguments."""
        class App(MLArgParser):
            def run(self, format: str = "text", verbose: bool = False):
                """Run with format and verbose."""
                pass

        with patch.object(sys, "argv", ["prog"]):
            app = App(noparse=True)
            app._MLArgParser__init_commands()
            app._MLArgParser__merge_arg_desc()
            parser = mlargparser_argcomplete.build_completion_parser(app)

        choices = _get_subparser_choices(parser)
        run_parser = choices["run"]
        option_strings = []
        for action in run_parser._actions:
            option_strings.extend(getattr(action, "option_strings", []))
        self.assertIn("--format", option_strings)
        self.assertIn("--verbose", option_strings)

    def test_subcommand_tree_structure(self):
        """Nested subcommand (type) produces nested subparsers."""
        class DumpCmd(MLArgParser):
            """Dump subcommand."""
            def config(self):
                """Dump config."""
                pass

            def state(self):
                """Dump state."""
                pass

        class MyApp(MLArgParser):
            """Top-level app."""
            dump = DumpCmd

        with patch.object(sys, "argv", ["prog"]):
            app = MyApp(noparse=True)
            app._MLArgParser__init_commands()
            app._MLArgParser__merge_arg_desc()
            parser = mlargparser_argcomplete.build_completion_parser(app)

        choices = _get_subparser_choices(parser)
        self.assertIn("dump", choices)
        dump_parser = choices["dump"]
        dump_choices = _get_subparser_choices(dump_parser)
        self.assertIsNotNone(dump_choices)
        self.assertIn("config", dump_choices)
        self.assertIn("state", dump_choices)

    def test_subcommand_with_args_has_options(self):
        """Subcommand method with args has options in completion parser."""
        class DumpCmd(MLArgParser):
            def config(self, format: str = "text"):
                """Dump config."""
                pass

        class MyApp(MLArgParser):
            dump = DumpCmd

        with patch.object(sys, "argv", ["prog"]):
            app = MyApp(noparse=True)
            app._MLArgParser__init_commands()
            app._MLArgParser__merge_arg_desc()
            parser = mlargparser_argcomplete.build_completion_parser(app)

        dump_parser = _get_subparser_choices(parser)["dump"]
        config_parser = _get_subparser_choices(dump_parser)["config"]
        option_strings = []
        for action in config_parser._actions:
            option_strings.extend(getattr(action, "option_strings", []))
        self.assertIn("--format", option_strings)


class TestArgcompleteModule(unittest.TestCase):
    """Test module API and install/uninstall (no argcomplete required)."""

    def test_argcomplete_available_is_bool(self):
        """ARGCOMPLETE_AVAILABLE is a boolean."""
        self.assertIsInstance(mlargparser_argcomplete.ARGCOMPLETE_AVAILABLE, bool)

    def test_install_noop_without_argcomplete(self):
        """install() is a no-op when argcomplete is not installed (does not raise)."""
        if mlargparser_argcomplete.ARGCOMPLETE_AVAILABLE:
            self.skipTest("argcomplete is installed")
        mlargparser_argcomplete.install()

    def test_uninstall_restores_when_patched(self):
        """uninstall() restores MLArgParser.__init__ if we had patched (and argcomplete present)."""
        if not mlargparser_argcomplete.ARGCOMPLETE_AVAILABLE:
            self.skipTest("argcomplete not installed")
        orig = MLArgParser.__init__
        mlargparser_argcomplete.install()
        self.assertIsNot(MLArgParser.__init__, orig)
        mlargparser_argcomplete.uninstall()
        self.assertIs(MLArgParser.__init__, orig)
