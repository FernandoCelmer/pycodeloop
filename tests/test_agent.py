from aiflow.abc.provider import Provider, ProviderResponse, ToolCall
from aiflow.abc.tool import Tool, ToolResult
from aiflow.core.agent import Agent


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)

    def complete(self, system_prompt, messages, tools, on_delta=None) -> ProviderResponse:
        return self._scripted.pop(0)


class EchoTool(Tool):
    name = "echo"
    description = "Echo the given text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, text: str) -> ToolResult:
        return ToolResult(output=f"echo: {text}")


class DeleteTool(Tool):
    name = "delete_everything"
    description = "Deletes everything."
    dangerous = True

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(output="deleted")


def test_agent_returns_text_when_no_tool_calls():
    provider = FakeProvider([ProviderResponse(text="hello")])
    agent = Agent(provider=provider, tools=[EchoTool()])

    result = agent.run("hi")

    assert result == "hello"


def test_agent_executes_tool_call_then_returns_final_text():
    provider = FakeProvider(
        [
            ProviderResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="echo", arguments={"text": "hey"})],
            ),
            ProviderResponse(text="done"),
        ]
    )
    calls = []
    agent = Agent(
        provider=provider,
        tools=[EchoTool()],
        on_tool_result=lambda name, result: calls.append((name, result)),
    )

    result = agent.run("do it")

    assert result == "done"
    assert calls == [("echo", "echo: hey")]


def test_agent_reports_unknown_tool():
    provider = FakeProvider(
        [
            ProviderResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="missing", arguments={})],
            ),
            ProviderResponse(text="ok"),
        ]
    )
    results = []
    agent = Agent(
        provider=provider,
        tools=[EchoTool()],
        on_tool_result=lambda _name, result: results.append(result),
    )

    agent.run("do it")

    assert results == ["Unknown tool: missing"]


def test_agent_skips_dangerous_tool_when_confirm_declines():
    provider = FakeProvider(
        [
            ProviderResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="delete_everything", arguments={})],
            ),
            ProviderResponse(text="ok"),
        ]
    )
    results = []
    agent = Agent(
        provider=provider,
        tools=[DeleteTool()],
        confirm=lambda _name, _preview: False,
        on_tool_result=lambda _name, result: results.append(result),
    )

    agent.run("do it")

    assert results == ["User declined to run this tool."]


def test_agent_runs_dangerous_tool_when_confirm_accepts():
    provider = FakeProvider(
        [
            ProviderResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="delete_everything", arguments={})],
            ),
            ProviderResponse(text="ok"),
        ]
    )
    results = []
    agent = Agent(
        provider=provider,
        tools=[DeleteTool()],
        confirm=lambda _name, _preview: True,
        on_tool_result=lambda _name, result: results.append(result),
    )

    agent.run("do it")

    assert results == ["deleted"]
