"""
Model Router - Manages local LLM routing and structured JSON output.
Includes robust JSON extraction that handles markdown blocks, extra text, and partial responses.
"""
import ollama
from pydantic import BaseModel
import json
import re
import config 

class ModelRouter:
    def __init__(self):
        self.fast_model = getattr(config, 'FAST_MODEL', None)
        self.deep_model = getattr(config, 'DEEP_MODEL', None)
        self.last_raw_output = None # Stores last raw LLM output for debugging

        # Auto-detect available models to prevent 404 errors
        try:
            response = ollama.list()
            if hasattr(response, 'models'):
                available = [m.model for m in response.models]
            else:
                available = [m.get('name') for m in response.get('models', [])]

            if self.deep_model not in available and available:
                print(f"⚠️  '{self.deep_model}' not found. Available: {available}")
                # Try to find a model that contains '14b' or fall back to first
                fallback = next((m for m in available if '14b' in m.lower()), available[0])
                self.deep_model = fallback
                print(f"🔄 Falling back deep_model to: {self.deep_model}")

            if self.fast_model not in available and available:
                fallback = next((m for m in available if '7b' in m.lower()), available[0])
                self.fast_model = fallback

        except Exception as e:
            print(f"⚠️  Could not verify Ollama models: {e}")

        print(f"✅ Model Router initialized:")
        print(f"   Fast model: {self.fast_model}")
        print(f"   Deep model: {self.deep_model}")

    def get_model(self, task_type='default'):
        if task_type == 'fast':
            return self.fast_model
        return self.deep_model

    def generate_text(self, prompt, system_prompt="", task_type='deep'):
        """Standard text generation."""
        model = self.get_model(task_type)
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ]
            )
            return response['message']['content']
        except Exception as e:
            print(f"    ⚠️  Model generation failed: {e}")
            return ""

    def _extract_json(self, text):
        """
        Robustly extract JSON from LLM output.
        Handles: markdown blocks, extra text, nested objects, arrays.
        """
        if not text:
            return None

        # Strip whitespace
        text = text.strip()

        # Try 1: Direct parse (cleanest case)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try 2: Remove markdown code blocks
        cleaned = re.sub(r'```(?:json)?\s*', '', text)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try 3: Find first { ... } block using regex
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try 4: Find JSON between first { and last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        # Try 5: Handle [ ... ] arrays
        first_bracket = text.find('[')
        last_bracket = text.rfind(']')
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            try:
                return json.loads(text[first_bracket:last_bracket + 1])
            except json.JSONDecodeError:
                pass

        return None

    def generate_structured_output(self, prompt, system_prompt, schema, task_type='deep', max_retries=2, options=None):
        """Generate structured output using the specified model."""
        schema_instructions = f"""
            You MUST output ONLY a valid JSON object. No markdown, no explanation, no code blocks, no nested wrappers.
            The JSON must have EXACTLY these top-level fields: {list(schema.model_fields.keys())}
            Do NOT group them into nested objects. Output a flat JSON object.
            Output raw JSON starting with {{ and ending with }}.
            """
        full_system_prompt = f"{system_prompt}\n{schema_instructions}"

        chat_options = {'temperature': 0.3}
        if options:
            chat_options.update(options)  # allows num_predict cap etc.

        for attempt in range(max_retries):
            try:
                model = self.get_model(task_type)

                response = ollama.chat(
                    model=model,
                    format='json',
                    messages=[
                        {'role': 'system', 'content': full_system_prompt},
                        {'role': 'user', 'content': prompt}
                    ],
                    options=chat_options
                )

                raw_output = response['message']['content']
                if getattr(config, 'VERBOSE_LOGGING', False):
                    print(f"🔍 [{self.__class__.__name__}] Raw LLM output: {raw_output[:200]}...")

                self.last_raw_output = raw_output
                parsed_json = self._extract_json(raw_output)

                if parsed_json is None:
                    if getattr(config, 'VERBOSE_LOGGING', False):
                        print(f"🧾 FULL RAW OUTPUT (repr): {repr(raw_output[:500])}")
                    raise ValueError(f"Could not extract JSON from LLM output: {raw_output[:100]}")

                parsed = schema(**parsed_json)
                return parsed

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Retry attempt {attempt + 1} for structured output: {str(e)[:100]}")
                    continue
                raise e

        return None

if __name__ == "__main__":
    router = ModelRouter()
    print(router.generate_text("What is the current US inflation rate?", task_type='fast'))