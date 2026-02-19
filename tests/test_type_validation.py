#!/usr/bin/env python3
"""Tests for type validation and error handling."""

import sys
import unittest
import io
from contextlib import redirect_stderr
from unittest.mock import patch

from mlargparser import MLArgParser, TypeValidator


class TestTypeValidator(unittest.TestCase):
    """Test TypeValidator utility methods."""

    def test_is_bool_type_simple(self):
        """Test is_bool_type with simple bool."""
        self.assertTrue(TypeValidator.is_bool_type(bool))
        self.assertFalse(TypeValidator.is_bool_type(int))
        self.assertFalse(TypeValidator.is_bool_type(str))

    def test_is_bool_type_optional(self):
        """Test is_bool_type with Optional[bool]."""
        try:
            from typing import Optional
            self.assertTrue(TypeValidator.is_bool_type(Optional[bool]))
        except ImportError:
            self.skipTest("typing.Optional not available")

    def test_is_valid_annotation_empty(self):
        """Test is_valid_annotation with empty annotation."""
        import inspect
        is_valid, error = TypeValidator.is_valid_annotation(inspect.Parameter.empty)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_is_valid_annotation_none(self):
        """Test is_valid_annotation with None."""
        is_valid, error = TypeValidator.is_valid_annotation(None)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_is_valid_annotation_string(self):
        """Test is_valid_annotation with string (invalid)."""
        is_valid, error = TypeValidator.is_valid_annotation("int")
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)

    def test_is_valid_annotation_callable(self):
        """Test is_valid_annotation with callable type."""
        is_valid, error = TypeValidator.is_valid_annotation(int)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_normalize_annotation_empty(self):
        """Test normalize_annotation with empty annotation."""
        import inspect
        result = TypeValidator.normalize_annotation(inspect.Parameter.empty)
        self.assertEqual(result, str)

    def test_normalize_annotation_none(self):
        """Test normalize_annotation with None."""
        result = TypeValidator.normalize_annotation(None)
        self.assertEqual(result, str)

    def test_normalize_annotation_type(self):
        """Test normalize_annotation with actual type."""
        result = TypeValidator.normalize_annotation(int)
        self.assertEqual(result, int)

    # Note: extract_base_type was removed as it was unused in the implementation


class TestInvalidTypeAnnotations(unittest.TestCase):
    """Test handling of invalid type annotations."""

    def test_string_annotation_error(self):
        """String annotations should raise error."""
        class App(MLArgParser):
            def cmd(self, value: "int"):  # String annotation
                pass

        app = App(noparse=True, strict_types=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            try:
                app._MLArgParser__init_commands()
                self.fail("Should have raised ValueError")
            except ValueError:
                pass  # Expected

    def test_string_annotation_warning_non_strict(self):
        """String annotations should warn in non-strict mode."""
        class App(MLArgParser):
            def cmd(self, value: "int"):  # String annotation
                pass

        app = App(noparse=True, strict_types=False)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__init_commands()
        
        # Should print warning but not raise
        output = stderr.getvalue()
        self.assertIn("Warning", output)

    def test_invalid_callable_error(self):
        """Non-callable annotations should raise error."""
        class App(MLArgParser):
            def cmd(self, value: 42):  # Invalid: not a type
                pass

        app = App(noparse=True, strict_types=True)
        try:
            app._MLArgParser__init_commands()
            self.fail("Should have raised ValueError")
        except ValueError:
            pass  # Expected


class TestStrictTypesMode(unittest.TestCase):
    """Test strict_types configuration."""

    def test_strict_types_raises_on_error(self):
        """strict_types=True should raise on validation errors."""
        class App(MLArgParser):
            def cmd(self, value: "invalid"):  # String annotation
                pass

        app = App(noparse=True, strict_types=True)
        try:
            app._MLArgParser__init_commands()
            self.fail("Should have raised ValueError")
        except ValueError:
            pass  # Expected

    def test_strict_types_false_warns_only(self):
        """strict_types=False should warn but not raise."""
        class App(MLArgParser):
            def cmd(self, value: "invalid"):  # String annotation
                pass

        app = App(noparse=True, strict_types=False)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            app._MLArgParser__init_commands()  # Should not raise
        
        output = stderr.getvalue()
        self.assertIn("Warning", output)


class TestComplexTypeAnnotations(unittest.TestCase):
    """Test complex type annotations."""

    def test_union_type(self):
        """Test Union type handling."""
        try:
            from typing import Union
        except ImportError:
            self.skipTest("typing.Union not available")

        class App(MLArgParser):
            def cmd(self, value: Union[int, str]):
                self.result = value

        # Union types use first non-None type
        with patch.object(sys, 'argv', ['prog', 'cmd', '--value', '42']):
            app = App()
            self.assertEqual(app.result, 42)

    def test_list_of_optional(self):
        """Test list[Optional[T]] handling."""
        try:
            from typing import Optional
        except ImportError:
            self.skipTest("typing.Optional not available")

        class App(MLArgParser):
            def cmd(self, items: list[Optional[str]]):
                self.result = items

        with patch.object(sys, 'argv', ['prog', 'cmd', '--items', 'a', 'b']):
            app = App()
            self.assertEqual(app.result, ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
