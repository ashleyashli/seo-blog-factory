import json
import os
import re
import time


class LLMClient:
    """Unified LLM client — supports OpenAI and Anthropic with retry."""

    def __init__(self, config):
        self.provider = config["llm"]["provider"]
        self.scoring_model = config["llm"].get("scoring_model", "gpt-4o-mini")
        self.writing_model = config["llm"].get("writing_model", "gpt-4o")
        self._init_client(config)

    def _init_client(self, config):
        if self.provider == "openai":
            from openai import OpenAI

            api_key = config["llm"].get("openai_api_key") or os.environ.get(
                "OPENAI_API_KEY"
            )
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. "
                    "Set 'openai_api_key' in config.yaml or export OPENAI_API_KEY."
                )
            base_url = config["llm"].get("base_url")
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

        elif self.provider == "anthropic":
            import anthropic

            api_key = config["llm"].get("anthropic_api_key") or os.environ.get(
                "ANTHROPIC_API_KEY"
            )
            if not api_key:
                raise ValueError(
                    "Anthropic API key required. "
                    "Set 'anthropic_api_key' in config.yaml or export ANTHROPIC_API_KEY."
                )
            self.client = anthropic.Anthropic(api_key=api_key)

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def chat(self, system_prompt, user_prompt, model=None, json_mode=False, max_retries=3):
        """Send a chat completion request with exponential-backoff retry."""
        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    return self._openai_chat(system_prompt, user_prompt, model, json_mode)
                else:
                    return self._anthropic_chat(system_prompt, user_prompt, model)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** (attempt + 1)
                print(f"  [!] LLM error (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"      Retrying in {wait}s...")
                time.sleep(wait)

    def _openai_chat(self, system_prompt, user_prompt, model, json_mode):
        kwargs = {
            "model": model or self.writing_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _anthropic_chat(self, system_prompt, user_prompt, model):
        response = self.client.messages.create(
            model=model or self.writing_model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def score(self, system_prompt, user_prompt):
        """Score a topic (cheap model, JSON output). Falls back if json_mode unsupported."""
        try:
            return self.chat(
                system_prompt, user_prompt, model=self.scoring_model, json_mode=True
            )
        except Exception:
            return self.chat(
                system_prompt, user_prompt, model=self.scoring_model, json_mode=False
            )

    def write(self, system_prompt, user_prompt):
        """Write a blog article (capable model, long-form output)."""
        return self.chat(system_prompt, user_prompt, model=self.writing_model)

    @staticmethod
    def extract_json(text):
        """Best-effort JSON extraction from LLM response."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            raise
