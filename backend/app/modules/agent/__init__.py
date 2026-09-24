"""
Agent module: the LangGraph-based conversational reasoning layer.

Unlike the CRUD modules, this is organized around a graph rather than
router/service/repository, because its job is orchestrating a multi-step
decision process (classify -> retrieve -> maybe call a tool -> generate
-> quality-check -> respond or hand off), not persisting a resource.
Implemented in Phase 5.
"""
