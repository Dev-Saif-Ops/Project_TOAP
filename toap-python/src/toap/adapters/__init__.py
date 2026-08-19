"""Optional framework adapters."""

__all__ = [
    "TOAPOutputParser",
    "toap_system_prompt",
    "TOAPExecutor",
    "build_toap_chain",
    "TOAPCrewCallback",
    "toap_task_prompt",
]


def __getattr__(name: str):
    if name in ("TOAPOutputParser", "toap_system_prompt", "TOAPExecutor", "build_toap_chain"):
        from toap.adapters.langchain import (
            TOAPOutputParser,
            toap_system_prompt,
            TOAPExecutor,
            build_toap_chain,
        )
        return {
            "TOAPOutputParser": TOAPOutputParser,
            "toap_system_prompt": toap_system_prompt,
            "TOAPExecutor": TOAPExecutor,
            "build_toap_chain": build_toap_chain,
        }[name]
    if name in ("TOAPCrewCallback", "toap_task_prompt", "build_toap_crew", "run_toap_crew", "TOAPCrewResult"):
        from toap.adapters.crewai import (
            TOAPCrewCallback,
            toap_task_prompt,
            build_toap_crew,
            run_toap_crew,
            TOAPCrewResult,
        )
        return {
            "TOAPCrewCallback": TOAPCrewCallback,
            "toap_task_prompt": toap_task_prompt,
            "build_toap_crew": build_toap_crew,
            "run_toap_crew": run_toap_crew,
            "TOAPCrewResult": TOAPCrewResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
