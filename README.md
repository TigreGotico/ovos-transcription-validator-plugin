# **OVOS Transcription Validator Plugin**

A plugin for [OVOS](https://openvoiceos.com) that uses an OpenAI-compatible Large Language Model (LLM) to validate
transcriptions from speech-to-text (STT) before they are processed by your voice assistant.

It helps filter out garbled, nonsensical, or incomplete utterances—reducing confusion and improving the accuracy of
downstream skills.

---

## **Features**

* Multilingual transcription validation
* Powered by OpenAI-compatible LLMs (e.g., OpenAI API, Ollama, custom servers)
* Filters out invalid utterances before processing
* Optional feedback via error sound or dialog
* Fully configurable, with per-request overrides

---

## **How It Works**

1. The plugin receives an STT transcription and language code.
2. A structured prompt with examples is sent to the configured OpenAI-compatible LLM API.
3. The LLM responds with True (valid) or False (invalid).
4. If invalid:
    * The utterance is canceled.
    * Optionally, a dialog prompt or error sound is triggered.

---

## **Installation**

```bash
pip install ovos-transcription-validator-plugin
```

---

## **Configuration**

Add the plugin to the utterance_transformers section of your mycroft.conf.

The plugin defaults to using https://llama.smartgic.io/v1 with qwen2.5:7b and a placeholder API key sk-xxxx.

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

### **Available Settings**

| Key                    | Description                                                                                                              | Default Value                |
|:-----------------------|:-------------------------------------------------------------------------------------------------------------------------|:-----------------------------|
| api_url                | The URL of your OpenAI-compatible LLM API endpoint.                                                                      | https://llama.smartgic.io/v1 |
| api_key                | Your API key for the LLM service. Set to null or omit if no key is required (e.g., some local Ollama setups).            | sk-xxxx (placeholder)        |
| model                  | The name of the LLM model to use (e.g., qwen2.5:7b, gpt-3.5-turbo, gemma3:1b).                                           | qwen2.5:7b                   |
| prompt_template_system | (Optional) Path to a .txt file to override the default system prompt for the LLM.                                        | (internal default)           |
| prompt_template_user   | (Optional) Path to a .txt file to override the default user prompt template for the LLM.                                 | (internal default)           |
| error_sound            | true to play a sound on error, false to disable, or a string path to a custom sound file.                                | false                        |
| mode                   | reprompt to ask the user to repeat the utterance, or ignore to silently cancel the invalid input.                        | ignore                       |
| max_tokens             | Maximum number of tokens for the LLM's response.                                                                         | 3                            |
| temperature            | LLM generation temperature. Lower values (e.g., 0.0) make the output more deterministic (good for True/False responses). | 0.0                          |
| top_p                  | LLM sampling parameter.                                                                                                  | 0.2                          |
| stop_token             | A list of strings that, if encountered, will cause the LLM to stop generating further tokens.                            | ["\n", " "]                   |
| api_timeout            | Timeout in seconds for the LLM API request.                                                                              | 10                           |

---

## **Requirements & Notes**

* Requires an OpenAI-compatible LLM API endpoint to be accessible (
  e.g., [OpenAI API](https://platform.openai.com/), [Ollama](https://ollama.ai) running locally, or another custom
  server).
* You must have a supported model already available on your chosen LLM server.
* The plugin can adapt to different languages based on the LLM's capabilities and training.

---

## **Feedback & Contributions**

Found a bug or want to contribute? PRs and issues are welcome!
