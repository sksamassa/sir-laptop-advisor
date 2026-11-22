"""Test package marker.

Without this, ``tests`` is a namespace package and pytest's import mode loads
``conftest`` as a top-level module, so ``from tests.helpers import ...`` fails.
"""
