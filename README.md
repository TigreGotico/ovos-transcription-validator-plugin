# OVOS Transcription Validator Plugin

This plugin is a [utterance transformer](https://openvoiceos.com) for OVOS. It uses an OpenAI-compatible large language model (LLM) to check speech-to-text (STT) transcriptions before your voice assistant processes them.

The plugin filters out garbled, nonsensical, or incomplete utterances. This reduces confusion and improves the accuracy of downstream skills.

---

## Features

- Validates transcriptions in multiple languages.
- Works with OpenAI-compatible LLMs (for example, the OpenAI API, Ollama, or a custom server).
- Filters out invalid utterances before the assistant processes them.
- Plays an error sound or shows a dialog when it rejects an utterance.
- Supports per-request configuration overrides.

---

## How It Works

1. The plugin receives an STT transcription and a language code.
2. It sends a structured prompt with examples to the configured OpenAI-compatible LLM API.
3. The LLM answers `True` (valid) or `False` (invalid).
4. If the LLM answers `False`, the plugin cancels the utterance. It also triggers a dialog prompt or an error sound if you configure one.

---

## Installation

```bash
pip install ovos-transcription-validator-plugin
```

---

## Configuration

Add the plugin to the `utterance_transformers` section of your `mycroft.conf`.

By default, the plugin uses `https://llama.smartgic.io/v1` with the `qwen2.5:7b` model and a placeholder API key `sk-xxxx`.

```json
{
  "utterance_transformers": {
    "ovos-transcription-validator-plugin": {
      "api_url": "https://llama.smartgic.io/v1",
      "api_key": "sk-xxxx",
      "model": "qwen2.5:7b",
      "prompt_template_system": "/path/to/system_template.txt",
      "prompt_template_user": "/path/to/user_template.txt",
      "error_sound": true,
      "mode": "ignore"
    }
  }
}
```

---

### Available Settings

| Key                     | Description                                                                                             | Default Value                 |
|:------------------------|:----------------------------------------------------------------------------------------------------------|:-------------------------------|
| api_url                 | The URL of your OpenAI-compatible LLM API endpoint.                                                        | https://llama.smartgic.io/v1   |
| api_key                 | Your API key for the LLM service. Set it to null, or omit it, if the service needs no key (some local Ollama setups). | sk-xxxx (placeholder)          |
| model                   | The name of the LLM model to use (for example, qwen2.5:7b, gpt-3.5-turbo, or gemma3:1b).                    | qwen2.5:7b                     |
| prompt_template_system  | Path to a .txt file that overrides the default system prompt for the LLM. Optional.                        | (internal default)             |
| prompt_template_user    | Path to a .txt file that overrides the default user prompt template for the LLM. Optional.                 | (internal default)             |
| error_sound             | Set to true to play a sound on error, false to disable it, or give a string path to a custom sound file.   | false                          |
| mode                    | Set to reprompt to ask the user to repeat the utterance, or ignore to cancel the invalid input silently.    | ignore                         |
| max_tokens              | The maximum number of tokens in the LLM's response.                                                         | 3                               |
| temperature             | The LLM generation temperature. Lower values (for example, 0.0) make the output more deterministic, which suits True/False responses. | 0.0                             |
| top_p                   | The LLM sampling parameter.                                                                                 | 0.2                             |
| stop_token              | A list of strings that stop the LLM from generating further tokens when it encounters them.                 | ["\n", " "]                    |
| api_timeout             | The timeout, in seconds, for the LLM API request.                                                           | 10                              |

---

## Requirements & Notes

- You need an OpenAI-compatible LLM API endpoint, for example the [OpenAI API](https://platform.openai.com/), [Ollama](https://ollama.ai) running locally, or another custom server.
- The model you configure must already be available on your chosen LLM server.
- The plugin adapts to different languages based on the LLM's capabilities and training.

---

## Related Projects

- [OpenVoiceOS](https://github.com/OpenVoiceOS) — the org that maintains the OVOS core and the utterance transformer framework this plugin extends.

---

## Feedback & Contributions

Found a bug or want to contribute? Open an issue or a pull request.
