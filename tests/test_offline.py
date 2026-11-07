"""Offline tests. They use a local stub server, so they need no Keln key and reach no Keln host.

Run from the plugin root: python tests/test_offline.py
"""

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["INSTALL_METHOD"] = "local"

from dify_plugin.config.config import DifyPluginEnv  # noqa: E402
from dify_plugin.core.plugin_registration import PluginRegistration  # noqa: E402
from dify_plugin.entities.model import ModelFeature, ModelType  # noqa: E402
from dify_plugin.entities.model.message import (  # noqa: E402
    AssistantPromptMessage,
    PromptMessageTool,
    ToolPromptMessage,
    UserPromptMessage,
)
from dify_plugin.errors.model import CredentialsValidateFailedError  # noqa: E402

MODEL = "zai-org/glm-5.3"
CREDENTIALS = {"api_key": "stub-value"}
TOOLS = [
    PromptMessageTool(
        name="add",
        description="Add 2 numbers",
        parameters={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
    )
]
TOOL_CALL = {"id": "call_1", "type": "function", "function": {"name": "add", "arguments": '{"a":1,"b":2}'}}
STREAM = [
    {"choices": [{"index": 0, "delta": {"role": "assistant"}}]},
    {"choices": [{"index": 0, "delta": {"reasoning_content": "Need a tool.", "reasoning": "Need a tool."}}]},
    {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, **TOOL_CALL}]}}]},
    {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
    {"id": "chatcmpl-keln", "choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}},
]
BLOCKING = {
    "id": "x",
    "object": "chat.completion",
    "model": MODEL,
    "choices": [{"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": [TOOL_CALL]}}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
}


class Stub(BaseHTTPRequestHandler):
    last_body: dict = {}
    last_auth: str = ""
    status: int = 200

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        Stub.last_body = json.loads(self.rfile.read(length))
        Stub.last_auth = self.headers.get("Authorization", "")
        if Stub.status != 200:
            self._send(Stub.status, b'{"error":{"message":"stub error","type":"keln_error"}}')
        elif Stub.last_body.get("stream"):
            lines = "".join(f"data: {json.dumps(item)}\n\n" for item in STREAM) + "data: [DONE]\n\n"
            self._send(200, lines.encode(), "text/event-stream")
        else:
            self._send(200, json.dumps(BLOCKING).encode())

    def _send(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.registration = PluginRegistration(DifyPluginEnv())
        cls.llm = cls.registration.get_model_instance("keln", ModelType.LLM)
        # The SDK loads plugin modules outside sys.modules, so patch the base URL through the method globals.
        cls.plugin_globals = type(cls.llm)._prepare_credentials.__globals__
        cls.real_base = cls.plugin_globals["KELN_API_BASE"]
        cls.plugin_globals["KELN_API_BASE"] = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.plugin_globals["KELN_API_BASE"] = cls.real_base
        cls.server.shutdown()

    def setUp(self):
        Stub.status = 200
        Stub.last_body = {}
        Stub.last_auth = ""

    def test_predefined_models(self):
        schemas = {schema.model: schema for schema in self.llm.predefined_models()}
        self.assertEqual(
            set(schemas),
            {
                "zai-org/glm-5.3",
                "zai-org/glm-5.3-flash",
                "moonshotai/kimi-k3",
                "qwen/qwen3.8-2.4t-a95b",
                "deepseek-ai/deepseek-v4.1-flash",
            },
        )
        self.assertEqual(self.registration.models_mapping["keln"][0].position.llm[0], MODEL)
        for schema in schemas.values():
            self.assertIn(ModelFeature.TOOL_CALL, schema.features)
            self.assertIsNone(schema.pricing)
            self.assertEqual(self.llm.get_price(schema.model, CREDENTIALS, _input(), 1000).total_amount, 0)

    def test_stream_sends_usage_option_and_drops_user(self):
        chunks = list(
            self.llm._invoke(MODEL, dict(CREDENTIALS), [UserPromptMessage(content="hi")], {"temperature": 0.5}, TOOLS, None, True, "end-user-1")
        )
        body = Stub.last_body
        self.assertEqual(body["model"], MODEL)
        self.assertEqual(body["stream_options"], {"include_usage": True})
        self.assertNotIn("user", body)
        self.assertEqual(body["tools"][0]["function"]["name"], "add")
        self.assertEqual(Stub.last_auth, "Bearer stub-value")

        text = "".join(chunk.delta.message.content or "" for chunk in chunks)
        self.assertEqual(text, "<think>\nNeed a tool.\n</think>")
        calls = [call for chunk in chunks for call in chunk.delta.message.tool_calls]
        self.assertEqual([call.function.name for call in calls], ["add"])
        self.assertEqual(chunks[-1].delta.usage.prompt_tokens, 11)
        self.assertEqual(chunks[-1].delta.usage.completion_tokens, 7)

    def test_blocking_tool_reply_with_null_content(self):
        result = self.llm._invoke(MODEL, dict(CREDENTIALS), [UserPromptMessage(content="hi")], {}, TOOLS, None, False, None)
        self.assertEqual(result.message.content, "")
        self.assertEqual(result.message.tool_calls[0].function.name, "add")
        self.assertNotIn("stream_options", Stub.last_body)

    def test_tool_history_moves_trace_to_reasoning_content(self):
        call = AssistantPromptMessage.ToolCall(
            id="call_1",
            type="function",
            function=AssistantPromptMessage.ToolCall.ToolCallFunction(name="add", arguments='{"a":1,"b":2}'),
        )
        history = [
            UserPromptMessage(content="hi"),
            AssistantPromptMessage(content="<think>\nNeed a tool.\n</think>", tool_calls=[call]),
            ToolPromptMessage(content="3", tool_call_id="call_1"),
            AssistantPromptMessage(content="<think>\nDone.\n</think>The answer is 3."),
        ]
        list(self.llm._invoke(MODEL, dict(CREDENTIALS), history, {}, TOOLS, None, True, None))
        messages = Stub.last_body["messages"]
        self.assertEqual(messages[1]["reasoning_content"], "Need a tool.")
        self.assertEqual(messages[1]["content"], "")
        self.assertEqual(messages[1]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(messages[3]["reasoning_content"], "Done.")
        self.assertEqual(messages[3]["content"], "The answer is 3.")

    def test_plain_assistant_text_is_unchanged(self):
        history = [AssistantPromptMessage(content="Text with <think> in the middle")]
        self.assertNotIn("reasoning_content", self.llm._convert_prompt_message_to_dict(history[0], {}))

    def test_validation_ok_and_rejected(self):
        self.llm.validate_credentials(MODEL, dict(CREDENTIALS))
        self.assertEqual(Stub.last_body["max_tokens"], 5)
        self.assertEqual(Stub.last_body["model"], MODEL)
        Stub.status = 401
        with self.assertRaises(CredentialsValidateFailedError) as caught:
            self.llm.validate_credentials(MODEL, dict(CREDENTIALS))
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("stub-value", str(caught.exception))

    def test_provider_validates_on_default_model(self):
        provider = self.registration.get_model_provider_instance("keln")
        provider.validate_provider_credentials(dict(CREDENTIALS))
        self.assertEqual(Stub.last_body["model"], MODEL)

    def test_custom_model_schema(self):
        schema = self.llm.get_customizable_model_schema("org/model", {"context_size": "131072", "max_tokens_to_sample": "32768"})
        rules = {rule.name: rule for rule in schema.parameter_rules}
        self.assertEqual(rules["max_tokens"].default, 8192)
        self.assertIn("reasoning_effort", rules)
        self.assertIn(ModelFeature.TOOL_CALL, schema.features)
        schema = self.llm.get_customizable_model_schema(
            "org/model", {"context_size": "131072", "function_calling_type": "no_call"}
        )
        self.assertNotIn(ModelFeature.TOOL_CALL, schema.features)


def _input():
    from dify_plugin.entities.model import PriceType

    return PriceType.INPUT


if __name__ == "__main__":
    unittest.main(verbosity=2)
