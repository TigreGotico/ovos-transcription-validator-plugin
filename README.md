# 🧠 OVOS Transcription Validator Plugin

This plugin uses a local or remote LLM (e.g., via [Ollama](https://ollama.ai)) to validate transcriptions from
speech-to-text (STT) engines before they are processed by a voice assistant.

It helps avoid processing nonsense, garbled, or incomplete transcriptions that can confuse downstream skills.

Supported languages will depend on the specific LLM you are using

## 💡 How It Works

1. Receives a transcribed utterance and language code.
2. Sends a prompt to an LLM with examples and the transcription.
3. The LLM responds with `True` or `False` based on whether the transcription is coherent and complete.
4. If the response is `False`, the utterance is canceled and tagged as a mistranscription.

## 📦 Installation

```bash
pip install ovos-transcription-validator-plugin
```

## ⚠️ Notes

- You need a local or network-accessible instance of Ollama.
- This plugin assumes you have the appropriate model (like `gemma3:1b`) installed in Ollama.

## 🔧 Configuration

Provides the utterance transformer plugin `"ovos-transcription-validator-plugin"`

Enable and configure it in your `mycroft.conf`

```json
{
 "utterance_transformers": {
      "ovos-transcription-validator-plugin": {
          "model": "gemma3:1b",
          "ollama_url": "http://192.168.1.200:11434",
          "prompt_template": "/path/to/template.txt",
          "error_sound": true
      }
  }
}
```

- `model`: The name of the model exposed by Ollama.
- `ollama_url`: URL to your Ollama instance.
- `prompt_template`: full path to a .txt file, if set will override the default template, more info below
- `error_sound`: wether to play a error sound on transcription error or not

### Default Prompt Template

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