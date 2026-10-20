from __future__ import annotations

import heapq

from dbtmini.errors import CycleError, DagError


def _find_cycle_path(
    unresolved: set[str], dependencies: dict[str, set[str]]
) -> list[str]:
    """
    Find a cycle in the dependency graph.
    param:
        unresolved: Set of nodes that are part of the cycle.
        dependencies: Mapping of model_name -> set of upstream models it depends on.
    return:
        List of model names in the cycle path.
    """
    visited: set[str] = set()
    path: list[str] = []
    path_index: dict[str, int] = {}

    def dfs(node: str) -> list[str] | None:
        visited.add(node)
        path.append(node)
        path_index[node] = len(path) - 1

        for dep in sorted(dependencies.get(node, set())):
            if dep not in unresolved:
                continue
            if dep in path_index:
                start_idx = path_index[dep]
                return path[start_idx:] + [dep]
            if dep not in visited:
                cycle = dfs(dep)
                if cycle:
                    return cycle

        del path_index[node]
        path.pop()
        return None

    for node in sorted(unresolved):
        if node not in visited:
            cycle = dfs(node)
            if cycle:
                return cycle
    return sorted(unresolved)


def topological_sort(dependencies: dict[str, set[str]]) -> list[str]:
    """
    Sort models in dependency order using Kahn's algorithm.

    param:
        dependencies: Mapping of model_name -> set of upstream models it depends on.
    return:
        List of model names in topological execution order (parents before children).
    raises:
        DagError: If a model references an unknown dependency.
        CycleError: If a dependency cycle is detected.
    """
    # Validate that all referenced dependencies are known models
    for model, deps in dependencies.items():
        for dep in deps:
            if dep not in dependencies:
                raise DagError(
                    f"Model '{model}' depends on unknown model '{dep}'",
                    model_name=model,
                )

    # dbt style of if model depends on dep,dep must run before model
    downstream: dict[str, list[str]] = {node: [] for node in dependencies}
    in_degree: dict[str, int] = {node: len(deps) for node, deps in dependencies.items()}

    for model, deps in dependencies.items():
        for dep in deps:
            downstream[dep].append(model)

    # Seed priority queue with in-degree 0 models (no prerequisites)
    ready: list[str] = [node for node, deg in in_degree.items() if deg == 0]
    heapq.heapify(ready)

    final: list[str] = []

    # Kahn's Algorithm
    while ready:
        top_node = heapq.heappop(ready)
        final.append(top_node)

        # unblock downstream models that depend on top_node
        for neighbour in downstream[top_node]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                heapq.heappush(ready, neighbour)

    if len(final) != len(dependencies):
        unresolved = {node for node, deg in in_degree.items() if deg > 0}
        cycle_path = _find_cycle_path(unresolved, dependencies)
        raise CycleError(
            message=f"Cycle detected: {' -> '.join(cycle_path)}",
            cycle_path=cycle_path,
        )

    return final
