"""Shared code for the skills' tools and for hooks.py.

The engine copies `lib/` into the trained model and puts the model root on `sys.path`, so a tool
imports it as `from lib.<module> import ...`. The fixture data lives in `lib/data/` for the same
reason. `context` is typed `Any` in these modules, so `lib/` imports no engine module, except
`authored_facts.py`, which uses the engine's response registry.
"""
