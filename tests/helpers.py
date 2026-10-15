"""Shared helpers for the current source tree's tests.

The old test helper targeted an abandoned Ed25519 licensing implementation
that is not present in this source tree. Keep imports lightweight so tests
exercise the implementation that is actually shipped.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
