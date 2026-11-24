"""videogen package: applies videogen/verified_copy.py on top of registry.APPS
(registry.py stays byte-identical to the iOS App Guide mirror; see verified_copy)."""

from . import registry as _registry
from . import verified_copy as _verified_copy

_verified_copy.apply(_registry.APPS)
