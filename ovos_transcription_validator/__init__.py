import json
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
from ovos_utils.log import LOG

# Default prompt for LLM validation
# This is formatted as a system message for OpenAI-compatible APIs,
# and will be combined with a user message for the actual query.
STT_VALIDATION_PROMPT_SYSTEM = """
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
"""
# User message template for the actual evaluation
STT_VALIDATION_PROMPT_USER_TEMPLATE = """
Language: {lang}
Sentence: "{transcribed_text}"
Answer:"""

# Constant for the cancel word used when a mistranscription is detected
MISTRANSCRIPTION_CANCEL_WORD = "[MISTRANSCRIPTION]"


class TranscriptionValidatorPlugin(UtteranceTransformer):
    """
    A plugin that uses an LLM to validate transcriptions from STT,
    ensuring only coherent and complete utterances are processed.

    This transformer intercepts utterances and sends them to a configured
    OpenAI-compatible LLM for validation. If the LLM determines an utterance
    is invalid (e.g., garbled, incomplete), the plugin can either reprompt
    the user or play an error sound, effectively canceling the processing
    of the invalid input.
    """

    def __init__(self, name: str = "ovos-transcription-validator", priority: int = 1):
        """
        Initialize the TranscriptionValidatorPlugin.

        Args:
            name (str): The name of the plugin. Defaults to "ovos-transcription-validator".
            priority (int): The priority of this transformer in the pipeline.
                            Lower numbers mean higher priority. Defaults to 1.
        """
        super().__init__(name, priority)
        self.dialogs: Dict[str, Dict[str, List[str]]] = defaultdict(dict)
        self.load_dialogs()

        # Load API configuration from mycroft.conf.
        # These are expected to be set in the OVOS configuration.
        # Default to public server values if not in config.
        self.api_key: Optional[str] = self.config.get("api_key", "sk-xxxx")
        self.api_url: str = self.config.get("api_url", "https://llama.smartgic.io/v1")
        self.model: str = self.config.get("model", "qwen2.5:7b")

    def load_dialogs(self):
        """
        Loads dialogs from the 'locale' directory for various languages.
        These dialogs are used for feedback to the user (e.g., "say again").
        Dialogs are expanded using bracket expansion and deduplicated.
        """
        path = os.path.join(os.path.dirname(__file__), "locale")

        if not os.path.exists(path):
            LOG.warning(f"Locale directory not found at: {path}")
            return

        for l in os.listdir(path):
            std = standardize_lang_tag(l)
            locale_dir = os.path.join(path, l)

            if not os.path.isdir(locale_dir):
                continue

            for root, dirs, files in os.walk(locale_dir):
                for f in files:
                    if f.endswith(".dialog"):
                        name = f.split(".dialog")[0]
                        file_path = os.path.join(root, f)
                        try:
                            with open(file_path, "r", encoding="utf-8") as fi:
                                examples = fi.read().split("\n")
                            # Expand templates and flatten the list, then deduplicate
                            expanded_examples = flatten_list([expand_template(t) for t in examples if t.strip()])
                            self.dialogs[name][std] = deduplicate_list(expanded_examples)
                        except Exception as e:
                            LOG.error(f"Error loading dialog file {file_path}: {e}")

    def get_dialog(self, name: str, lang: str) -> Optional[str]:
        """
        Retrieves a random dialog string for a given name and language.
        It attempts to find the closest matching language if an exact match
        is not available, using `langcodes.tag_distance`.

        Args:
            name (str): The name of the dialog (e.g., "say_again").
            lang (str): The language code (e.g., "en-US", "pt-PT").

        Returns:
            Optional[str]: A random dialog string from the closest matching
                           language, or None if no suitable dialog is found.
        """
        standardized_lang = standardize_lang_tag(lang)
        best_match_lang: Optional[str] = None
        min_distance: float = float('inf')

        for available_lang in self.dialogs[name]:
            distance = tag_distance(standardized_lang, available_lang)
            if distance < min_distance:
                min_distance = distance
                best_match_lang = available_lang

        # A low score (e.g., < 10) indicates a close language match.
        # Adjust this threshold if needed.
        if best_match_lang and min_distance < 10:
            dialogs = self.dialogs[name].get(best_match_lang)
            if dialogs:
                return random.choice(dialogs)
        return None

    def _do_llm_api_request(self,
                            messages: List[Dict[str, str]],
                            model: str,
                            api_url: str,
                            api_key: Optional[str]
                            ) -> Optional[str]:
        """
        Send a chat completion request to an OpenAI-compatible API and return the assistant's reply.

        Parameters:
            messages (List[Dict[str, str]]): Conversation history as a list of message dictionaries.
                                              Each dictionary should have "role" and "content" keys.
            model (str): The name of the LLM model to use (e.g., "gpt-3.5-turbo", "gemma3:1b").
            api_url (str): The URL of the OpenAI-compatible API endpoint.
            api_key (Optional[str]): The API key for authentication. Can be None if the API
                                     does not require a key (e.g., some local Ollama setups).

        Returns:
            Optional[str]: The assistant's reply content (stripped of leading/trailing whitespace),
                           or None if the request fails or the response is malformed.

        Raises:
            RequestException: If the API response contains an error (handled internally and logged).
        """
        if not api_url:
            LOG.error("LLM API URL not configured.")
            return None

        s = requests.Session()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer " + api_key

        # Parameters for OpenAI-compatible API
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.config.get("max_tokens", 3),
            "temperature": self.config.get("temperature", 0.0),  # Set low for deterministic answers (True/False)
            "top_p": self.config.get("top_p", 0.2),
            "n": 1,
            "frequency_penalty": self.config.get("frequency_penalty", 0),
            "presence_penalty": self.config.get("presence_penalty", 0),
            "stop": self.config.get("stop_token", ["\n", " "])  # Stop at newline for single-line True/False
        }
        url = api_url + "/chat/completions"
        try:
            response = s.post(url, headers=headers, data=json.dumps(payload), timeout=self.config.get("api_timeout", 10))
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            result = response.json()
            if "error" in result:
                # Specific error message from the API
                error_message = result["error"].get("message", "Unknown API error")
                error_type = result["error"].get("type", "N/A")
                LOG.error(f"LLM API returned an error: Type={error_type}, Message='{error_message}'")
                return None
            return result["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            LOG.error(f"LLM API request timed out after {self.config.get('api_timeout', 10)} seconds.")
            return None
        except requests.exceptions.ConnectionError as e:
            LOG.error(f"LLM API connection error: {e}. Is the API server running and accessible?")
            return None
        except requests.exceptions.RequestException as e:
            LOG.error(f"LLM API request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            LOG.error(
                f"Unexpected LLM API response structure: {e}. Response: {response.text if response else 'No response'}")
            return None

    def validate_transcriptions_llm(self,
                                    utterance: str,
                                    lang: str,
                                    model: str,
                                    api_url: str,
                                    api_key: Optional[str]
                                    ) -> Optional[bool]:
        """
        Validate a transcribed utterance using an OpenAI-compatible LLM.

        This method constructs the prompt for the LLM based on configured
        system and user prompt templates, then sends the request to the LLM
        API. It expects a "True" or "False" response from the LLM.

        Args:
            utterance (str): The transcribed sentence from STT.
            lang (str): The language code of the utterance (e.g., 'en', 'pt').
            model (str): The name of the LLM model to use (e.g., "gpt-3.5-turbo", "gemma3:1b").
            api_url (str): The URL of the OpenAI-compatible API endpoint.
            api_key (Optional[str]): The API key for authentication.

        Returns:
            Optional[bool]: True if the utterance is deemed valid by the LLM,
                            False if it's a mistranscription, or None on API error.
        """
        # Load system prompt template from file path if provided, otherwise use default
        system_prompt_path: Optional[str] = self.config.get("prompt_template_system")
        system_prompt: str = STT_VALIDATION_PROMPT_SYSTEM
        if system_prompt_path:
            try:
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read()
            except FileNotFoundError:
                LOG.error(f"System prompt template file not found: {system_prompt_path}. Using default system prompt.")
            except Exception as e:
                LOG.error(f"Error reading system prompt template file {system_prompt_path}: {e}. Using default system prompt.")

        # Load user prompt template from file path if provided, otherwise use default
        user_prompt_path: Optional[str] = self.config.get("prompt_template_user")
        user_template: str = STT_VALIDATION_PROMPT_USER_TEMPLATE
        if user_prompt_path:
            try:
                with open(user_prompt_path, "r", encoding="utf-8") as f:
                    user_template = f.read()
            except FileNotFoundError:
                LOG.error(f"User prompt template file not found: {user_prompt_path}. Using default user prompt.")
            except Exception as e:
                LOG.error(f"Error reading user prompt template file {user_prompt_path}: {e}. Using default user prompt.")

        # Format the user prompt with the current utterance and language
        formatted_user_prompt: str = user_template.format(
            transcribed_text=utterance, lang=lang
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_user_prompt}
        ]

        # Call the LLM API with the provided model, API URL, and API key
        result: Optional[str] = self._do_llm_api_request(
            messages, model, api_url, api_key
        )

        if result is not None:
            return result.lower() == "true"
        return None

    def transform(self, utterances: List[str], context: Optional[dict] = None) -> Tuple[List[str], dict]:
        """
        Filter out invalid utterances using the configured LLM.

        This method is the core of the UtteranceTransformer. It takes a list
        of utterances (typically a single one from STT) and a context dictionary.
        It determines the language, calls the LLM to validate the utterance,
        and then decides whether to allow the utterance to proceed, reprompt
        the user, or play an error sound based on the validation result and
        plugin configuration.

        Args:
            utterances (List[str]): A list of transcribed utterances.
                                    Typically, this list contains a single string.
            context (Optional[dict]): A dictionary containing additional metadata,
                                      such as 'lang' (language code), 'session'
                                      (OVOS Session object), and optional
                                      'model', 'api_url', 'api_key' overrides.

        Returns:
            Tuple[List[str], dict]: A tuple containing:
                                    - A filtered list of utterances (empty if canceled).
                                    - A dictionary with metadata, including 'canceled'
                                      (True if the utterance was rejected) and
                                      'cancel_word' (reason for cancellation).
        """
        context = context or {}
        lang: str
        if "lang" in context:
            lang = context.get("lang", "en-US")
        elif "session" in context:
            lang = Session.deserialize(context["session"]).lang
        else:
            # Fallback to default session manager language
            sess = SessionManager.get()
            lang = sess.lang

        standardized_lang: str = standardize_lang_tag(lang)

        # If no utterances are provided or the first one is empty, do nothing
        if not utterances or not utterances[0].strip():
            return utterances, {}

        # Determine LLM parameters with priority: context > instance config defaults
        llm_model: str = context.get("model", self.model)
        llm_api_url: str = context.get("api_url", self.api_url)
        llm_api_key: Optional[str] = context.get("api_key", self.api_key)

        # Let the LLM decide if this was a STT error or a valid utterance
        is_valid: Optional[bool] = self.validate_transcriptions_llm(
            utterances[0],
            lang=standardized_lang,
            model=llm_model,
            api_url=llm_api_url,
            api_key=llm_api_key
        )

        if is_valid is False:  # Explicitly check for False, not just None
            mode: str = self.config.get("mode", "ignore")
            default_sound: str = Configuration().get("sounds", {}).get("error", "snd/error.mp3")
            sound_config: Union[str, bool] = self.config.get("error_sound", False)
            play_error_sound: bool = False

            if mode == "reprompt" and self.bus:
                dialog: Optional[str] = self.get_dialog("say_again", standardized_lang)
                if dialog:
                    self.bus.emit(Message("speak",
                                          {"utterance": dialog,
                                           "listen": True,
                                           "lang": standardized_lang}))
                    # Return metadata similar to ovos-utterance-cancel-plugin
                    return [], {"canceled": True, "cancel_word": MISTRANSCRIPTION_CANCEL_WORD}
                else:
                    # If reprompt dialog is missing for the language, play error sound
                    LOG.warning(f"No 'say_again' dialog found for language '{standardized_lang}'. Playing error sound.")
                    play_error_sound = True
            elif mode == "ignore":
                play_error_sound = bool(sound_config) # Play sound only if explicitly configured for 'ignore' mode

            # Play an error sound if configured or if reprompt failed
            if play_error_sound and self.bus:
                sound_uri: str = default_sound
                if isinstance(sound_config, str):
                    sound_uri = sound_config
                self.bus.emit(Message("mycroft.audio.play_sound",
                                      {"uri": sound_uri}))

            # Return metadata similar to ovos-utterance-cancel-plugin
            return [], {"canceled": True, "cancel_word": MISTRANSCRIPTION_CANCEL_WORD}
        elif is_valid is None:
            # LLM API call failed, log and proceed as if valid (or handle differently based on policy)
            LOG.error("LLM validation failed due to API error. Treating utterance as valid.")
            return utterances, {} # Proceed with the original utterance
        else: # is_valid is True
            return utterances, {}


if __name__ == "__main__":
    # Example usage for testing
    # This part assumes you have an OpenAI-compatible server running (e.g., OpenAI API, Ollama)
    # and have configured mycroft.conf appropriately for testing.
    # For local testing without a full OVOS environment, you might need to mock the bus and config.

    print("\n--- Testing LLM-compatible API ---")
    plugin_llm = TranscriptionValidatorPlugin()

    # The plugin's __init__ now defaults to the specified public server settings.
    # You can still override them here for specific test cases if needed.
    # For example, to test with OpenAI:
    # plugin_llm.config["model"] = "gpt-3.5-turbo"
    plugin_llm.config["api_url"] = "http://192.168.1.200:11434"
    # plugin_llm.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")

    # The default settings are:
    # api_url: "https://llama.smartgic.io/v1"
    # model: "qwen2.5:7b"
    # api_key: "sk-xxxx" (placeholder, replace if using a real key for this server)

    # Create dummy prompt files for testing
    dummy_system_prompt_path = "dummy_system_prompt.txt"
    with open(dummy_system_prompt_path, "w", encoding="utf-8") as f:
        f.write("You are a helpful and strict assistant that validates sentences. Respond only with 'True' or 'False'.")
    plugin_llm.config["prompt_template_system"] = dummy_system_prompt_path

    dummy_user_prompt_path = "dummy_user_prompt.txt"
    with open(dummy_user_prompt_path, "w", encoding="utf-8") as f:
        f.write("""
Please evaluate the following.
Language: {lang}
Sentence: "{transcribed_text}"
Is this valid? Answer:
""")
    plugin_llm.config["prompt_template_user"] = dummy_user_prompt_path

    # Mock the bus for testing purposes if not running in a full OVOS environment
    class MockBus:
        def emit(self, message: Message):
            print(f"MockBus emitted: {message.msg_type} - {message.data}")

    plugin_llm.bus = MockBus() # Assign the mock bus

    test_utterances_llm = ["Play the next song.", "Potato stop green light now yes.", "Liga as luzes da sala.", "Céu laranja vai cadeira não som.", "Hello world.", ""]
    test_languages = ["en-US", "en-US", "pt-PT", "pt-PT", "en-US", "en-US"]

    print("\n--- Testing with default (public server) configuration ---")
    for i, utt in enumerate(test_utterances_llm):
        lang = test_languages[i]
        print(f"\nTesting utterance: '{utt}' in language: '{lang}' (Default Config)")
        # Call transform without explicit overrides in context
        result_utt, result_ctx = plugin_llm.transform([utt], {"lang": lang})
        print(f"LLM Validation - Utterance: '{utt}', Valid: {not result_ctx.get('canceled', False)}")
        if result_ctx.get('canceled', False):
            print(f"  Reason: {result_ctx.get('cancel_word', 'Unknown')}")
        print(f"  Returned utterances: {result_utt}")


    # Clean up dummy prompt files
    if os.path.exists(dummy_system_prompt_path):
        os.remove(dummy_system_prompt_path)
    if os.path.exists(dummy_user_prompt_path):
        os.remove(dummy_user_prompt_path)
