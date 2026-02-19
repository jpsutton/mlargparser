#!/usr/bin/env python3
"""Integration tests for complete workflows."""

import sys
import unittest
from unittest.mock import patch

from mlargparser import MLArgParser


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete end-to-end workflows."""

    def test_complex_command(self):
        """Test a complex command with multiple argument types."""
        class App(MLArgParser):
            arg_desc = {
                "name": "User name",
                "age": "User age",
                "tags": "Tags for the user",
                "verbose": "Enable verbose output"
            }

            def create_user(self, name: str, age: int, tags: list[str] = None, verbose: bool = False):
                """Create a new user."""
                self.result = {
                    "name": name,
                    "age": age,
                    "tags": tags or [],
                    "verbose": verbose
                }

        with patch.object(sys, 'argv', [
            'prog', 'create-user', '--name', 'Alice', '--age', '30',
            '--tags', 'admin', 'user', '--verbose'
        ]):
            app = App()
            self.assertEqual(app.result["name"], "Alice")
            self.assertEqual(app.result["age"], 30)
            self.assertEqual(app.result["tags"], ["admin", "user"])
            self.assertTrue(app.result["verbose"])

    def test_multiple_commands_workflow(self):
        """Test workflow with multiple commands."""
        class App(MLArgParser):
            def init(self, name: str):
                """Initialize project."""
                self.init_result = name

            def build(self, target: str = "release"):
                """Build project."""
                self.build_result = target

            def deploy(self, environment: str, force: bool = False):
                """Deploy project."""
                self.deploy_result = (environment, force)

        # Test init
        with patch.object(sys, 'argv', ['prog', 'init', '--name', 'myproject']):
            app = App()
            self.assertEqual(app.init_result, "myproject")

        # Test build
        with patch.object(sys, 'argv', ['prog', 'build']):
            app = App()
            self.assertEqual(app.build_result, "release")

        # Test deploy
        with patch.object(sys, 'argv', ['prog', 'deploy', '--environment', 'prod', '--force']):
            app = App()
            self.assertEqual(app.deploy_result, ("prod", True))

    def test_boolean_flag_workflow(self):
        """Test workflow with boolean flags."""
        class App(MLArgParser):
            def process(self, input_file: str, output_file: str = None,
                       verbose: bool = False, cache: bool = True):
                """Process a file."""
                self.result = {
                    "input": input_file,
                    "output": output_file,
                    "verbose": verbose,
                    "cache": cache
                }

        # Without flags
        with patch.object(sys, 'argv', ['prog', 'process', '--input-file', 'input.txt']):
            app = App()
            self.assertFalse(app.result["verbose"])
            self.assertTrue(app.result["cache"])  # Default True

        # With flags
        with patch.object(sys, 'argv', [
            'prog', 'process', '--input-file', 'input.txt',
            '--verbose', '--no-cache'
        ]):
            app = App()
            self.assertTrue(app.result["verbose"])
            self.assertFalse(app.result["cache"])

    def test_list_argument_workflow(self):
        """Test workflow with list arguments."""
        class App(MLArgParser):
            def install(self, packages: list[str], dev: bool = False):
                """Install packages."""
                self.result = {
                    "packages": packages,
                    "dev": dev
                }

        # Single invocation
        with patch.object(sys, 'argv', [
            'prog', 'install', '--packages', 'pkg1', 'pkg2', 'pkg3'
        ]):
            app = App()
            self.assertEqual(app.result["packages"], ["pkg1", "pkg2", "pkg3"])

        # Multiple invocations
        with patch.object(sys, 'argv', [
            'prog', 'install', '--packages', 'pkg1', '--packages', 'pkg2', 'pkg3'
        ]):
            app = App()
            self.assertEqual(app.result["packages"], ["pkg1", "pkg2", "pkg3"])


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios."""

    def test_git_like_interface(self):
        """Test a git-like command interface."""
        class GitApp(MLArgParser):
            def commit(self, message: str, amend: bool = False):
                """Commit changes."""
                self.result = {"message": message, "amend": amend}

            def push(self, remote: str = "origin", force: bool = False):
                """Push changes."""
                self.result = {"remote": remote, "force": force}

            def pull(self, remote: str = "origin", rebase: bool = False):
                """Pull changes."""
                self.result = {"remote": remote, "rebase": rebase}

        # Commit
        with patch.object(sys, 'argv', ['prog', 'commit', '--message', 'Fix bug']):
            app = GitApp()
            self.assertEqual(app.result["message"], "Fix bug")
            self.assertFalse(app.result["amend"])

        # Push with force
        with patch.object(sys, 'argv', ['prog', 'push', '--force']):
            app = GitApp()
            self.assertTrue(app.result["force"])

    def test_docker_like_interface(self):
        """Test a docker-like command interface."""
        class DockerApp(MLArgParser):
            def build(self, tag: str, file: str = "Dockerfile", 
                     cache: bool = True):
                """Build an image."""
                self.result = {"tag": tag, "file": file, "cache": cache}

            def run(self, image: str, detach: bool = False, 
                   ports: list[str] = None):
                """Run a container."""
                self.result = {"image": image, "detach": detach, "ports": ports or []}

        # Build with required tag
        with patch.object(sys, 'argv', ['prog', 'build', '--tag', 'myapp:latest']):
            app = DockerApp()
            self.assertEqual(app.result["tag"], "myapp:latest")
            self.assertEqual(app.result["file"], "Dockerfile")  # Default value
            self.assertTrue(app.result["cache"])  # Default value

        # Build with no-cache flag
        with patch.object(sys, 'argv', ['prog', 'build', '--tag', 'myapp:latest', '--no-cache']):
            app = DockerApp()
            self.assertEqual(app.result["tag"], "myapp:latest")
            self.assertFalse(app.result["cache"])

        # Run with ports
        with patch.object(sys, 'argv', [
            'prog', 'run', '--image', 'myapp', '--ports', '8080:80', '--detach'
        ]):
            app = DockerApp()
            self.assertEqual(app.result["ports"], ["8080:80"])
            self.assertTrue(app.result["detach"])


if __name__ == '__main__':
    unittest.main()
