"""LangChain runnable helpers — optional langchain_core dependency."""

from __future__ import annotations

from typing import Any

from toap.parser import TOAPParser, ParseResult
from toap.prompts import build_system_prompt
from toap.proxy import TOAPProxy, ToolRegistry, InterceptResult


def toap_system_prompt(task: str, *, shots: int = 2) -> str:
    return build_system_prompt(task, shots=shots)


class TOAPOutputParser:
    """Parse LLM output as TOAP. Works standalone or as LangChain output parser."""

    def __init__(self):
        self._parser = TOAPParser()

    def parse(self, text: str) -> ParseResult:
        return self._parser.parse(text)

    def parse_text(self, text: str) -> dict[str, Any]:
        result = self._parser.parse(text)
        if not result.valid:
            msgs = "; ".join(e.message for e in result.errors)
            raise ValueError(f"Invalid TOAP: {msgs}")
        return result.to_dict()

    @classmethod
    def as_langchain_parser(cls):
        try:
            from langchain_core.output_parsers import BaseOutputParser
        except ImportError as exc:
            raise ImportError("pip install toap[langchain]") from exc

        toap_parser = cls()

        class _LCWrapper(BaseOutputParser[dict]):
            def parse(self, text: str) -> dict:
                return toap_parser.parse_text(text)

            def get_format_instructions(self) -> str:
                return build_system_prompt("{task}", shots=2)

        return _LCWrapper()


class TOAPExecutor:
    """LangChain Runnable wrapper: raw TOAP string -> InterceptResult."""

    def __init__(self, proxy: TOAPProxy, *, execute: bool = True):
        self.proxy = proxy
        self.execute = execute

    def invoke(self, raw: str) -> InterceptResult:
        return self.proxy.intercept(raw, execute=self.execute)

    def as_runnable(self):
        """Return langchain_core RunnableLambda for LCEL chains."""
        try:
            from langchain_core.runnables import RunnableLambda
        except ImportError as exc:
            raise ImportError("pip install toap[langchain]") from exc

        executor = self

        def _run(raw: str) -> dict[str, Any]:
            result = executor.invoke(raw)
            return {
                "valid": result.parsed.valid,
                "thought": result.parsed.thought,
                "namespace": result.parsed.namespace,
                "args": result.parsed.args,
                "executed": result.executed,
                "return_value": result.return_value,
                "error": result.error,
                "raw": raw,
            }

        return RunnableLambda(_run)


def build_toap_chain(llm, task: str, registry: ToolRegistry, *, shots: int = 2):
    """Build LCEL chain: prompt | llm | parse | execute.

    Returns (chain, proxy) where chain.invoke({}) runs end-to-end.
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
    except ImportError as exc:
        raise ImportError("pip install langchain-core") from exc

    proxy = TOAPProxy(registry)
    system = toap_system_prompt(task, shots=shots)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system}"),
        ("human", "Execute the task above. Respond in TOAP format only."),
    ])

    chain = (
        prompt.partial(system=system)
        | llm
        | StrOutputParser()
        | TOAPExecutor(proxy).as_runnable()
    )
    return chain, proxy
