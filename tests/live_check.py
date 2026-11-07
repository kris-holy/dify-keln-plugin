"""Real-key check of the plugin classes against api.keln.ai. It makes 4 billed requests.

The key comes only from the KELN_API_KEY environment variable. This script does not print or write it.
Run from the plugin root: python tests/live_check.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["INSTALL_METHOD"] = "local"

from dify_plugin.config.config import DifyPluginEnv  # noqa: E402
from dify_plugin.core.plugin_registration import PluginRegistration  # noqa: E402
from dify_plugin.entities.model import ModelType  # noqa: E402
from dify_plugin.entities.model.message import (  # noqa: E402
    AssistantPromptMessage,
    PromptMessageTool,
    ToolPromptMessage,
    UserPromptMessage,
)

MODEL = sys.argv[1] if len(sys.argv) > 1 else "zai-org/glm-5.3"
PARAMETERS = {"max_tokens": 2048, "reasoning_effort": "low"}
TOOLS = [
    PromptMessageTool(
        name="add",
        description="Add 2 numbers and return the sum.",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
]


def collect(chunks):
    text, calls, usage = "", [], None
    for chunk in chunks:
        text += chunk.delta.message.content or ""
        calls += chunk.delta.message.tool_calls or []
        usage = chunk.delta.usage or usage
    return text, calls, usage


def main():
    key = os.environ.get("KELN_API_KEY")
    if not key:
        sys.exit("Set KELN_API_KEY in this shell first. See TEST.md.")
    credentials = {"api_key": key}
    llm = PluginRegistration(DifyPluginEnv()).get_model_instance("keln", ModelType.LLM)

    llm.validate_credentials(MODEL, dict(credentials))
    print(f"PASS credential check on {MODEL}")

    prompt = [UserPromptMessage(content="Reply with the single word: ready")]
    text, _, usage = collect(llm._invoke(MODEL, dict(credentials), prompt, dict(PARAMETERS), None, None, True, None))
    print(f"chat reply: {text!r}")
    print(f"chat usage: prompt={usage.prompt_tokens} completion={usage.completion_tokens}")
    assert "ready" in text.lower(), "chat reply did not contain the word"
    print("PASS streaming chat")

    prompt = [UserPromptMessage(content="Use the add tool to add 1234 and 5678. Then state the sum.")]
    text, calls, _ = collect(llm._invoke(MODEL, dict(credentials), prompt, dict(PARAMETERS), TOOLS, None, True, None))
    assert calls, "the model made no tool call"
    call = calls[0]
    arguments = json.loads(call.function.arguments)
    print(f"tool call: {call.function.name} {arguments}")
    assert call.function.name == "add"
    prompt += [
        AssistantPromptMessage(content=text, tool_calls=[call]),
        ToolPromptMessage(content=str(arguments["a"] + arguments["b"]), tool_call_id=call.id),
    ]
    sent = llm._convert_prompt_message_to_dict(prompt[1], {"function_calling_type": "tool_call"})
    print(f"trace replayed in reasoning_content: {bool(sent.get('reasoning_content'))}")
    text, _, _ = collect(llm._invoke(MODEL, dict(credentials), prompt, dict(PARAMETERS), TOOLS, None, True, None))
    print(f"final reply: {text!r}")
    assert "6912" in text.replace(",", ""), "the final reply did not state 6912"
    print("PASS two-turn tool call")


if __name__ == "__main__":
    main()
