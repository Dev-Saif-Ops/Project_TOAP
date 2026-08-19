"""LangChain adapter tests — no live API required."""

from toap import ToolRegistry
from toap.adapters.langchain import TOAPOutputParser, TOAPExecutor, build_toap_chain
from toap.proxy import TOAPProxy


SAMPLE_TOAP = (
    '§T[sec_vuln_huawei_2026]\n'
    'ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5'
)


def test_output_parser():
    parser = TOAPOutputParser()
    result = parser.parse(SAMPLE_TOAP)
    assert result.valid
    assert result.namespace == "DB_SRC"


def test_build_toap_chain_with_fake_llm():
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    registry = ToolRegistry()
    registry.register("DB_SRC", lambda q, l=10: {"q": q, "l": l})

    llm = FakeListChatModel(responses=[SAMPLE_TOAP])
    chain, proxy = build_toap_chain(
        llm,
        "Query the database for Huawei Cloud vulnerabilities, limit 5",
        registry,
        shots=2,
    )

    result = chain.invoke({})
    assert result["valid"] is True
    assert result["namespace"] == "DB_SRC"
    assert result["executed"] is True
    assert result["return_value"]["q"] == "Huawei Cloud vulnerabilities"


def test_executor_runnable():
    registry = ToolRegistry()
    registry.register("DB_SRC", lambda q, l=10: {"ok": True})
    proxy = TOAPProxy(registry)
    executor = TOAPExecutor(proxy)
    runnable = executor.as_runnable()
    out = runnable.invoke('ƒ(DB_SRC)>q:"test"|l:1')
    assert out["executed"] is True
