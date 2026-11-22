"""Shared kernel: value types and ports used by every bounded context.

Deliberately limited to identifiers, money, errors, and the clock port so that
contexts stay decoupled (see docs/adr and the constitution, Principle II).
"""
