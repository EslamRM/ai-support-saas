"""
One function per graph node (classify, retrieve, generate, quality_check,
handoff, etc). Each node is a plain function: (state) -> partial state
update, independently unit-testable without running the whole graph.
"""
