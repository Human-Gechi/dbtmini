import pytest

from dbtmini.dag import topological_sort
from dbtmini.errors import CycleError, DagError


def test_empty_graph() -> None:
    assert topological_sort({}) == []


def test_single_node_no_deps() -> None:
    assert topological_sort({"a": set()}) == ["a"]


def test_linear_chain() -> None:
    graph = {
        "a": set(),
        "b": {"a"},
        "c": {"b"},
    }
    assert topological_sort(graph) == ["a", "b", "c"]


def test_diamond_graph() -> None:
    graph = {
        "a": set(),
        "b": {"a"},
        "c": {"a"},
        "d": {"b", "c"},
    }
    # "b" and "c" are both ready after "a", tie-broken alphabetically -> b before c
    assert topological_sort(graph) == ["a", "b", "c", "d"]


def test_disconnected_components_tie_breaking() -> None:
    graph: dict[str, set[str]] = {
        "x": set(),
        "a": set(),
    }
    assert topological_sort(graph) == ["a", "x"]


def test_wide_fan_out() -> None:
    graph = {
        "root": set(),
        "c": {"root"},
        "b": {"root"},
        "a": {"root"},
    }
    assert topological_sort(graph) == ["root", "a", "b", "c"]


def test_wide_fan_in() -> None:
    graph = {
        "c": set(),
        "b": set(),
        "a": set(),
        "sink": {"a", "b", "c"},
    }
    assert topological_sort(graph) == ["a", "b", "c", "sink"]


def test_deterministic_ordering() -> None:
    graph: dict[str, set[str]] = {
        "d": set(),
        "c": set(),
        "b": set(),
        "a": set(),
    }
    first_run = topological_sort(graph)
    for _ in range(5):
        assert topological_sort(graph) == first_run
    assert first_run == ["a", "b", "c", "d"]


def test_unknown_dependency_raises_dag_error() -> None:
    graph = {
        "orders": {"missing_customers"},
    }
    with pytest.raises(DagError, match="unknown model 'missing_customers'"):
        topological_sort(graph)


def test_self_referencing_cycle() -> None:
    graph = {
        "self_loop": {"self_loop"},
    }
    with pytest.raises(CycleError, match="Cycle detected"):
        topological_sort(graph)


def test_two_node_cycle() -> None:
    graph = {
        "a": {"b"},
        "b": {"a"},
    }
    with pytest.raises(CycleError) as exc_info:
        topological_sort(graph)
    assert len(exc_info.value.cycle_path) >= 2


def test_three_node_cycle() -> None:
    graph = {
        "a": {"c"},
        "b": {"a"},
        "c": {"b"},
    }
    with pytest.raises(CycleError, match="Cycle detected"):
        topological_sort(graph)


def test_cycle_in_disconnected_part() -> None:
    graph = {
        "valid_node": set(),
        "loop1": {"loop2"},
        "loop2": {"loop1"},
    }
    with pytest.raises(CycleError, match="Cycle detected"):
        topological_sort(graph)
