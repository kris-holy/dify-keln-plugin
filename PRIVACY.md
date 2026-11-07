# Privacy Policy

This plugin connects Dify to the Keln inference API at `https://api.keln.ai`.

## What the plugin sends

When you run a Keln model in Dify, the plugin sends the request that Dify builds to Keln over HTTPS,
so the model can generate a reply:

- your prompts, conversation history and system instructions, which can contain personal data if you
  or your users enter it
- images you attach
- tool definitions and tool results
- model parameters
- your Keln API key, to authenticate the request

When you save a key or add a model, the plugin sends 1 short chat request to check it.

The plugin sends this data only to `api.keln.ai`. It does not forward the Dify end-user ID, and it
does not turn on Keln's web search.

## What the plugin stores

The plugin does not collect, store or log your data. It sends no telemetry. Dify stores your API key
as a provider credential.

## How Keln handles your data

Keln's [Privacy Policy](https://keln.ai/privacy) and
[Privacy & zero data retention](https://docs.keln.ai/capabilities/privacy/) page govern this
processing. They state that:

- Keln processes prompts and completions in memory only to produce a response. Keln does not store
  them and does not use them to train models.
- Keln keeps operational metadata for billing, reliability and abuse prevention: timestamps, model,
  token counts, cost, latency, routing outcome, status and which of your API keys made the request.
- To serve a request, Keln routes it to independent third-party compute providers. Keln routes only
  to providers that operate zero data retention and have stated that they serve inference in memory
  only and do not store or train on your content. Requests leave Keln with no account ID, API key or
  IP address.
- When you sign up, Keln receives your name, email and organization, and uses them to run the service
  and to respond to you.

Those pages are authoritative. Read them in full for retention, sharing and your rights.

## Contact

For questions about this policy, write to contact@keln.ai.
