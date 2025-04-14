import os
import random
from collections import defaultdict
from typing import List, Optional, Tuple, Union, Dict

import requests
from langcodes import tag_distance
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session, SessionManager
from ovos_config import Configuration
from ovos_plugin_manager.templates.transformers import UtteranceTransformer
from ovos_utils.bracket_expansion import expand_template
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.list_utils import deduplicate_list, flatten_list

STT_VALIDATION_PROMPT_MULTI = """
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
Answer:"""


class TranscriptionValidatorPlugin(UtteranceTransformer):
    """
    A plugin that uses an LLM to validate transcriptions from STT,
    ensuring only coherent and complete utterances are processed.
    """

    def __init__(self, name: str = "ovos-transcription-validator", priority: int = 1):
        """
        Initialize the plugin.

        Args:
            name (str): Plugin name.
            priority (int): Transformer priority.
        """
        super().__init__(name, priority)
        self.dialogs: Dict[str, Dict[str, List[str]]] = defaultdict(dict)
        self.load_dialogs()

    def load_dialogs(self):
        path = os.path.join(os.path.dirname(__file__), "locale")

        for l in os.listdir(path):
            std = standardize_lang_tag(l)

            for root, dirs, files in os.walk(os.path.join(path, l)):
                for f in files:
                    if f.endswith(".dialog"):
                        name = f.split(".dialog")[0]
                        with open(os.path.join(root, f), "r", encoding="utf-8") as fi:
                            examples = fi.read().split("\n")
                        examples = flatten_list([expand_template(t) for t in examples])
                        self.dialogs[name][std] = deduplicate_list(examples)

    def get_dialog(self, name: str, lang: str) -> Optional[str]:
        lang = standardize_lang_tag(lang)
        for l2 in self.dialogs[name]:
            score = tag_distance(lang, l2)
            if score < 10:
                dialogs = self.dialogs[name][l2]
                return random.choice(dialogs)

    def validate_transcriptions_ollama(self,
                                       utterance: str,
                                       lang: str,
                                       model: str = "gemma3:1b",
                                       base_url: str = "http://0.0.0.0:11434"
                                       ) -> Optional[bool]:
        """
        Validate a transcribed utterance using a multilingual LLM via Ollama.

        Args:
            utterance (str): The transcribed sentence from STT.
            lang (str): The language code of the utterance (e.g., 'en', 'pt').
            model (str): The name of the model to query in Ollama.
            base_url (str): The base URL of the Ollama API.

        Returns:
            Optional[bool]: True if valid utterance, False if mistranscribed, None on error.
        """
        user_template = self.config.get("prompt_template")
        if user_template:
            # TODO - add some validation here
            with open(user_template, "r") as f:
                prompt_template = f.read()
        else:
            prompt_template = STT_VALIDATION_PROMPT_MULTI
        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt_template.format(transcribed_text=utterance, lang=lang),
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 1,
                        "stop": ["\n"]
                    }
                },
                timeout=10
            )
            result = response.json()["response"].strip()
            return result.lower() == "true"
        except Exception as e:
            return None

    def transform(self, utterances: List[str], context: Optional[dict] = None) -> Tuple[List[str], dict]:
        """
        Filter out invalid utterances using a language model.

        Args:
            utterances (List[str]): List of utterances (usually length 1).
            context (Optional[dict]): Additional metadata, including language/session info.

        Returns:
            Tuple[List[str], dict]: Filtered utterances and optional metadata.
        """
        context = context or {}
        if "lang" in context:
            lang = context.get("lang", "en-US")
        elif "session" in context:
            lang = Session.deserialize(context["session"]).lang
        else:
            sess = SessionManager.get()
            lang = sess.lang

        lang = standardize_lang_tag(lang)
        model = self.config.get("model", "gemma3:1b")
        url = self.config.get("ollama_url", "http://0.0.0.0:11434")

        # let a LLM decide if this was a STT error or a valid utterance
        is_valid = self.validate_transcriptions_ollama(utterances[0], model=model, lang=lang, base_url=url)
        if not is_valid:
            mode = self.config.get("mode", "ignore")
            default_sound = Configuration().get("sounds", {}).get("error", "snd/error.mp3")
            sound: Union[str, bool] = self.config.get("error_sound", False)

            if mode == "reprompt" and self.bus:
                dialog = self.get_dialog("say_again", lang)
                if dialog:
                    self.bus.emit(Message("speak",
                                          {"utterance": dialog,
                                           "listen": True,
                                           "lang": lang}))
                    # return metadata similar to ovos-utterance-cancel-plugin
                    return [], {"canceled": True, "cancel_word": "[MISTRANSCRIPTION]"}
                else:
                    # play error sound if dialog is untranslated to lang
                    sound = sound or True

            # play a error sound
            if sound and self.bus:
                if isinstance(sound, bool):
                    sound = default_sound
                self.bus.emit(Message("mycroft.audio.play_sound",
                                      {"uri": sound}))

            # return metadata similar to ovos-utterance-cancel-plugin
            return [], {"canceled": True, "cancel_word": "[MISTRANSCRIPTION]"}

        return utterances, {}


if __name__ == "__main__":
    s = TranscriptionValidatorPlugin()
    print(s.dialogs)
    print(s.get_dialog("say_again", "en"))
