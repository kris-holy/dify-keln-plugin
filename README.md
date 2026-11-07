# Keln for Dify

Use [Keln](https://keln.ai) models in [Dify](https://dify.ai) through Keln's OpenAI-compatible API at
`https://api.keln.ai/v1`.

Keln is an inference platform for open models with an OpenAI-compatible API. Keln maintains this
plugin. It is not affiliated with Dify or LangGenius.

- Source repository: https://github.com/kris-holy/dify-keln-plugin
- Docs: https://docs.keln.ai
- Contact: kris@keln.ai

## Setup

1. Sign up at [app.keln.ai](https://app.keln.ai/signup). Open **Keys** → **Create key** and copy the
   key.
2. In Dify, open **Integrations** → **Model Provider** and install **Keln**.
3. Choose **Add API Key** on the Keln card, paste the key and save.

Dify checks the key with 1 short chat request to `zai-org/glm-5.3`. Keln bills this request at its
normal rate. If the check returns `402`, your Keln balance is empty: top it up on the **Billing**
page, then save again.

## Usage

Pick a Keln model in any LLM node, agent or chatbot. The plugin lists these 5 models, all with tool
calling:

| Model | Context | Input | Reasoning effort |
|---|---|---|---|
| `zai-org/glm-5.3` | 1,048,576 | text | `low`, `high`, `max` |
| `zai-org/glm-5.3-flash` | 1,048,576 | text, images | `low`, `high`, `max` |
| `moonshotai/kimi-k3` | 1,048,576 | text, images | `none`, `low`, `high`, `max` |
| `qwen/qwen3.8-2.4t-a95b` | 1,010,000 | text | `low`, `medium`, `xhigh` |
| `deepseek-ai/deepseek-v4.1-flash` | 1,048,576 | text, images | `none`, `low`, `high`, `max` |

- **Tool calling:** use these models in agents and function-call nodes, with streamed tool calls, and
  parallel calls where the model supports them.
- **Image input:** turn on vision in your app to send images to the models marked with images.
- **Reasoning effort:** this setting chooses how much a model reasons before answering. Keln runs
  the deepest level of the model when you leave it unset, and bills reasoning as output tokens. Dify
  shows the reasoning trace as a thinking block. In tool-calling conversations the plugin sends the
  trace back to Keln in `reasoning_content`.
- **Max Tokens:** this cap covers reasoning and answer together. The plugin defaults to 8,192 and
  allows up to 32,768. Raise it if a long reasoning run leaves the answer short. Keln rejects a
  request when the prompt plus Max Tokens exceeds the context of the model.
- **Structured output:** set **Response Format** to `json_object` or `json_schema`.

### Other models

To use another chat model from the [live catalog](https://api.keln.ai/v1/models):

1. Choose **Add Model** on the Keln card.
2. Enter the model `id` from the catalog, and its `context_length` as **Context size**.
3. Set **Tool calling** and **Vision** for the model. If requests return `tools_not_supported`, set
   **Tool calling** to **Not supported**.

Dify sends 1 short chat request to check the model.

`cloudflare/clef` and `typesafe/jev-1.14` are decision models. They answer typed questions through
`/v1/decisions` and do not write text, so they do not work as chat models in this plugin.

## Credentials

| Field | Required | Description |
|---|---|---|
| API Key | yes | Your Keln API key, from **Keys** → **Create key**. Dify stores it as a provider credential. |

## Connection requirements

Your Dify instance needs outbound HTTPS access to `api.keln.ai`. The plugin uses the fixed base URL
`https://api.keln.ai/v1` and connects to no other host.

## Pricing

This plugin declares no prices, so Dify's logs show a cost of 0 for Keln models. Keln bills your
account at the rates on [Models & pricing](https://docs.keln.ai/models-pricing/). Your **Usage** page
shows the cost of each request.

## Privacy and footprint

- **Network:** the plugin sends your requests, including prompts, images and tool definitions, to
  `https://api.keln.ai` using your Keln API key. See [PRIVACY.md](PRIVACY.md) and
  [Privacy & zero data retention](https://docs.keln.ai/capabilities/privacy/).
- **Code:** the plugin registers 1 model provider. It runs no shell commands or background processes
  and reads no files outside its package.
- **End users:** the plugin does not forward the Dify end-user ID.
- **Telemetry:** the plugin sends no telemetry.

## Support

Open an issue at https://github.com/kris-holy/dify-keln-plugin/issues or write to kris@keln.ai.

## Changelog

- **0.0.1:** first release.

## License

MIT
