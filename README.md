# 🧠 OVOS Transcription Validator Plugin

A plugin for [OVOS](https://openvoiceos.com) that uses a local or remote LLM (e.g., [Ollama](https://ollama.ai)) to validate transcriptions from speech-to-text (STT) before they are processed by your voice assistant.

It helps filter out garbled, nonsensical, or incomplete utterances—reducing confusion and improving the accuracy of downstream skills.

> ⚠️ **Private Repository:** This project is not yet publicly available. Please do not share this repository outside the early access group.

---

## ✨ Features

- ✅ Multilingual transcription validation
- 🧠 Powered by LLMs (via Ollama)
- 🎯 Filters out invalid utterances before processing
- 🔉 Optional feedback via error sound or dialog
- ⚙️ Fully configurable

---

## ⚙️ How It Works

1. The plugin receives an STT transcription and language code.
2. A structured prompt with examples is sent to the LLM.
3. The LLM responds with `True` (valid) or `False` (invalid).
4. If invalid:
   - The utterance is canceled.
   - Optionally, a dialog prompt or error sound is triggered.

---

## 📦 Installation

```bash
git clone https://github.com/HiveMindInsiders/ovos-transcription-validator-plugin
pip install ovos-transcription-validator-plugin
```

---

## 🛠 Configuration

Add the plugin to the `utterance_transformers` section of your `mycroft.conf`:

```json
{
  "utterance_transformers": {
    "ovos-transcription-validator-plugin": {
      "model": "gemma3:1b",
      "ollama_url": "http://192.168.1.200:11434",
      "prompt_template": "/path/to/template.txt",
      "error_sound": true,
      "mode": "reprompt"
    }
  }
}
```

### Available Settings

| Key               | Description                                                      |
|------------------|------------------------------------------------------------------|
| `model`           | Name of the LLM model exposed via Ollama (e.g., `gemma3:1b`)     |
| `ollama_url`      | URL of your local/network-accessible Ollama instance             |
| `prompt_template` | (Optional) Path to a `.txt` file to override the default prompt  |
| `error_sound`     | `true` to play a sound on error                                  |
| `mode`            | `reprompt` to ask user to repeat, or `ignore` to silently cancel |

---

## 🧾 Default Prompt Template

If no custom prompt is provided, this default multilingual template is used:

```text
You are a multilingual language model helping a voice assistant determine if transcribed user input from speech-to-text (STT) is valid or not.

This system supports user input in multiple languages: English (en), Portuguese (pt), Spanish (es), Catalan (ca), Galician (gl), Basque (eus), Italian (it), French (fr), German (de), Dutch (nl), and Danish (da).

You will receive:
- the language code of the utterance
- the transcribed sentence

Respond only with:
- `True` if the sentence is valid, complete and coherent in the specified language.
- `False` if the sentence is clearly garbled, incomplete, nonsensical, or the result of a transcription error.

### Examples:
Language: en  
Sentence: "Play the next song."  
Answer: True

Language: en  
Sentence: "Potato stop green light now yes."  
Answer: False

Language: pt  
Sentence: "Liga as luzes da sala."  
Answer: True

Language: pt  
Sentence: "Céu laranja vai cadeira não som."  
Answer: False

### Now evaluate the next sentence.
Language: {lang}  
Sentence: "{transcribed_text}"  
Answer:
```

---

## ⚠️ Requirements & Notes

- Requires [Ollama](https://ollama.ai) running locally or accessible over the network.
- You must have a supported model (like `gemma3:1b`) already installed in Ollama.
- The plugin can adapt to different languages based on the LLM's capabilities and training.

---

## 💬 Feedback & Contributions

Found a bug or want to contribute? PRs and issues are welcome!
