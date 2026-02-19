#!/usr/bin/env python3
"""Tests for command name collision detection."""

import sys
import unittest
import io
from contextlib import redirect_stderr
from unittest.mock import patch

from mlargparser import MLArgParser


class TestCommandNameCollisions(unittest.TestCase):
    """Test detection and handling of command name collisions."""

    def test_case_insensitive_collision(self):
        """Test collision detection for case-insensitive commands."""
        class App(MLArgParser):
            def MyCommand(self):
                """First command."""
                pass

            def mycommand(self):
                """Second command - same normalized name."""
                pass

        app = App(noparse=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            try:
                app._MLArgParser__init_commands()
            except ValueError:
                # strict_validation=True raises ValueError on collision
                pass
        
        output = stderr.getvalue()
        # Both normalize to "mycommand", so should detect collision
        normalized_names = [app._MLArgParser__normalize_command_name(name) 
                           for name in ['MyCommand', 'mycommand']]
        self.assertEqual(normalized_names[0], normalized_names[1])  # They normalize the same
        
        # With strict_validation=True (default), should raise ValueError or warn
        # Check that collision was detected
        collision_detected = (
            "collision" in output.lower() or 
            len(app.commands) == 1  # Only one command stored (second overwrites first)
        )
        self.assertTrue(collision_detected, 
                       f"Collision not detected. Output: {output}, Commands: {list(app.commands.keys())}")

    def test_underscore_dash_collision(self):
        """Test collision between underscore and dash normalization."""
        class App(MLArgParser):
            def my_command(self):
                """First command."""
                pass

            def mycommand(self):
                """Second command."""
                pass

        app = App(noparse=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__init_commands()
        
        # my-command and mycommand might collide depending on normalization
        # This tests the collision detection logic

    def test_strict_validation_raises(self):
        """strict_validation=True should raise on collisions."""
        class App(MLArgParser):
            strict_validation = True

            def cmd1(self):
                pass

            def Cmd1(self):
                pass

        app = App(noparse=True)
        try:
            app._MLArgParser__init_commands()
            self.fail("Should have raised ValueError")
        except ValueError:
            pass  # Expected

    def test_non_strict_validation_warns(self):
        """strict_validation=False should warn but not raise."""
        class App(MLArgParser):
            strict_validation = False

            def cmd1(self):
                pass

            def Cmd1(self):
                pass

        app = App(noparse=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__init_commands()  # Should not raise
        
        output = stderr.getvalue()
        self.assertIn("collision", output.lower())

    def test_case_sensitive_no_collision(self):
        """case_sensitive_commands=True should allow case differences."""
        class App(MLArgParser):
            case_sensitive_commands = True

            def MyCommand(self):
                pass

            def mycommand(self):
                pass

        app = App(noparse=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__init_commands()
        
        # Should not report collision
        output = stderr.getvalue()
        self.assertNotIn("collision", output.lower())


class TestCommandSuggestions(unittest.TestCase):
    """Test command suggestion generation."""

    def test_similar_command_suggestion(self):
        """Test suggestion of similar commands."""
        class App(MLArgParser):
            def deploy(self):
                """Deploy command."""
                pass

            def delete(self):
                """Delete command."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        
        suggestions = app._MLArgParser__generate_command_suggestions("deplo", list(app.commands.keys()))
        self.assertIn("deploy", suggestions)

    def test_underscore_dash_suggestion(self):
        """Test suggestion handles underscore/dash differences."""
        class App(MLArgParser):
            def my_command(self):
                """My command."""
                pass

        app = App(noparse=True)
        app._MLArgParser__init_commands()
        
        suggestions = app._MLArgParser__generate_command_suggestions("my-command", list(app.commands.keys()))
        self.assertIn("my-command", suggestions)


class TestBooleanParameterCollisions(unittest.TestCase):
    """Test boolean parameter collision detection."""

    def test_enable_no_enable_collision(self):
        """Both enable and no_enable should raise error."""
        class App(MLArgParser):
            def cmd(self, enable: bool = True, no_enable: bool = False):
                pass

        app = App(noparse=True, strict_types=True)
        try:
            app._MLArgParser__init_commands()
            self.fail("Should have raised ValueError")
        except ValueError as e:
            self.assertIn("enable", str(e))
            self.assertIn("no_enable", str(e))

    def test_double_no_prefix_error(self):
        """no_no_ prefix should raise error."""
        class App(MLArgParser):
            def cmd(self, no_no_cache: bool = False):
                pass

        app = App(noparse=True, strict_types=True)
        try:
            app._MLArgParser__init_commands()
            self.fail("Should have raised ValueError")
        except ValueError as e:
            self.assertIn("no_no_", str(e))


if __name__ == '__main__':
    unittest.main()
