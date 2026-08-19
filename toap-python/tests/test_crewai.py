"""CrewAI adapter tests — no live API required."""

from unittest.mock import MagicMock, patch

from toap import ToolRegistry
from toap.adapters.crewai import (
    TOAPCrewCallback,
    build_toap_crew,
    run_toap_crew,
    toap_task_prompt,
)

SAMPLE_TOAP = (
    '§T[sec_vuln_huawei_2026]\n'
    'ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5'
)


def test_toap_task_prompt():
    prompt = toap_task_prompt("Query database", shots=2)
    assert "TOAP" in prompt
    assert "Query database" in prompt


def test_crew_callback_handle():
    registry = ToolRegistry()
    registry.register("DB_SRC", lambda q, l=10: {"q": q, "l": l})
    callback = TOAPCrewCallback(registry)
    parsed = callback.handle(SAMPLE_TOAP)
    assert parsed.valid
    assert parsed.namespace == "DB_SRC"
    assert callback.history[-1]["executed"] is True


def test_run_toap_crew_with_mock_kickoff():
    registry = ToolRegistry()
    registry.register("DB_SRC", lambda q, l=10: {"q": q, "l": l})

    mock_crew = MagicMock()
    mock_output = MagicMock()
    mock_output.raw = SAMPLE_TOAP
    mock_crew.kickoff.return_value = mock_output

    callback = TOAPCrewCallback(execute=False)
    result = run_toap_crew(mock_crew, callback, registry, execute=True)

    assert result.parsed.valid
    assert result.executed
    assert result.return_value["q"] == "Huawei Cloud vulnerabilities"


def test_build_toap_crew_structure():
    crew, callback, agent, task = build_toap_crew(
        "Test task", llm="gemini/gemini-3.5-flash-lite", shots=2
    )
    assert crew is not None
    assert callback is not None
    assert "TOAP" in task.description
    assert agent.role == "TOAP Protocol Agent"
