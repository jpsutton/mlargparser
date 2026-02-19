#!/usr/bin/env python3
"""Tests for CmdArg class."""

import unittest
import inspect

from mlargparser import CmdArg, TypeValidator, STR_UNDOCUMENTED


def _make_param(name, annotation=inspect.Parameter.empty, default=inspect.Parameter.empty):
    """Helper to create an inspect.Parameter for testing."""
    return inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                             default=default, annotation=annotation)


class TestCmdArgCreation(unittest.TestCase):
    """Test CmdArg object creation."""

    def test_string_parameter(self):
        """Test creating CmdArg for string parameter."""
        param = _make_param("name", str)
        arg = CmdArg(param, "User name")
        
        self.assertEqual(arg.name, "name")
        self.assertEqual(arg.type, str)
        self.assertEqual(arg.desc, "User name")
        self.assertEqual(arg.action, "store")
        self.assertEqual(arg.required, True)

    def test_integer_parameter(self):
        """Test creating CmdArg for integer parameter."""
        param = _make_param("count", int)
        arg = CmdArg(param, "Item count")
        
        self.assertEqual(arg.name, "count")
        self.assertEqual(arg.type, int)
        self.assertEqual(arg.action, "store")
        self.assertEqual(arg.required, True)

    def test_optional_parameter(self):
        """Test creating CmdArg for optional parameter."""
        param = _make_param("value", str, "default")
        arg = CmdArg(param, "A value")
        
        self.assertEqual(arg.required, False)

    def test_collection_parameter(self):
        """Test creating CmdArg for collection parameter."""
        param = _make_param("items", list[str])
        arg = CmdArg(param, "List of items")
        
        self.assertEqual(arg.action, "append")
        self.assertEqual(arg.nargs, "+")


class TestCmdArgBooleanHandling(unittest.TestCase):
    """Test CmdArg boolean flag handling."""

    def test_bool_false_default(self):
        """Test boolean with False default."""
        param = _make_param("verbose", bool, False)
        arg = CmdArg(param, "Enable verbose")
        
        self.assertEqual(arg.action, "store_true")
        self.assertFalse(arg.required)
        self.assertIsNone(arg.parser)

    def test_bool_true_default(self):
        """Test boolean with True default."""
        param = _make_param("cache", bool, True)
        arg = CmdArg(param, "Use cache")
        
        self.assertEqual(arg.action, "store_true")
        self.assertFalse(arg.required)

    def test_no_prefix_bool(self):
        """Test boolean parameter with no_ prefix."""
        param = _make_param("no_cache", bool, True)
        arg = CmdArg(param, "Disable cache")
        
        self.assertEqual(arg.action, "store_false")
        self.assertFalse(arg.required)


class TestCmdArgGetKwargs(unittest.TestCase):
    """Test get_argparse_kwargs method."""

    def test_string_kwargs(self):
        """Test kwargs for string parameter."""
        param = _make_param("name", str)
        arg = CmdArg(param, "Name")
        kwargs = arg.get_argparse_kwargs()
        
        self.assertEqual(kwargs['help'], "Name")
        self.assertEqual(kwargs['required'], True)
        self.assertEqual(kwargs['dest'], "name")
        self.assertEqual(kwargs['action'], "store")
        self.assertEqual(kwargs['type'], str)

    def test_boolean_kwargs(self):
        """Test kwargs for boolean parameter."""
        param = _make_param("verbose", bool, False)
        arg = CmdArg(param, "Verbose")
        kwargs = arg.get_argparse_kwargs()
        
        self.assertEqual(kwargs['action'], "store_true")
        self.assertNotIn('type', kwargs)

    def test_no_prefix_kwargs(self):
        """Test kwargs for no_ prefix parameter."""
        param = _make_param("no_cache", bool, True)
        arg = CmdArg(param, "Disable cache")
        kwargs = arg.get_argparse_kwargs()
        
        self.assertEqual(kwargs['dest'], "cache")  # Should strip no_ prefix
        self.assertEqual(kwargs['action'], "store_false")

    def test_list_kwargs(self):
        """Test kwargs for list parameter."""
        param = _make_param("items", list[str])
        arg = CmdArg(param, "Items")
        kwargs = arg.get_argparse_kwargs()
        
        self.assertEqual(kwargs['action'], "append")
        self.assertEqual(kwargs['nargs'], "+")
        self.assertIn('type', kwargs)


class TestCmdArgTypeValidation(unittest.TestCase):
    """Test type validation in CmdArg."""

    def test_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        param = _make_param("value", "int")  # String annotation
        
        with self.assertRaises(ValueError):
            CmdArg(param, "Value")

    def test_valid_type_passes(self):
        """Test that valid type passes validation."""
        param = _make_param("value", int)
        arg = CmdArg(param, "Value")
        
        self.assertIsNotNone(arg)


if __name__ == '__main__':
    unittest.main()
