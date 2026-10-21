"""
Translator Module - Translates non-English news to English for AI analysis.
Uses local Ollama model (qwen3:4b) for unlimited, free, private translation.
10-20x faster than Google Translate with no rate limits!
"""
import ollama
import os
import json
from datetime import datetime
from config import TRANSLATION_MODEL


LANGUAGE_NAMES = {
 'sv': 'Swedish',
 'da': 'Danish',
 'no': 'Norwegian',
 'ja': 'Japanese',
 'zh': 'Chinese',
 'de': 'German',
 'fr': 'French',
 'es': 'Spanish',
 'it': 'Italian',
 'nl': 'Dutch',
 'fi': 'Finnish',
 'en': 'English',
 'unknown': 'Unknown'
}

def get_language_name(lang_code):
    """Return a readable name for a language code."""
    return LANGUAGE_NAMES.get(lang_code, lang_code)

## ----

TRANSLATION_MODEL = os.getenv('TRANSLATION_MODEL', 'qwen3:4b')

class NewsTranslator:
    def __init__(self, target_language='en', cache_dir='data/translation_cache'):
        self.target_language = target_language
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._cache = self._load_cache()
        self._stats = {'translated': 0, 'cached': 0, 'failed': 0}

    def _load_cache(self):
        """Load translation cache from disk"""
        cache_file = os.path.join(self.cache_dir, 'translations.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Save translation cache to disk"""
        cache_file = os.path.join(self.cache_dir, 'translations.json')
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"    ⚠️  Could not save translation cache: {e}")

    def _get_cache_key(self, text, source_lang):
        """Generate cache key for a translation"""
        return f"{source_lang}:{text[:200]}"

    def translate_text(self, text, source_lang=None):
        """
        Translate text to English using local Ollama model.
        Returns (translated_text, detected_language)
        """
        if not text or len(text.strip()) < 3:
            return text, source_lang or 'unknown'

        # Check cache first
        cache_key = self._get_cache_key(text, source_lang or 'auto')
        if cache_key in self._cache:
            self._stats['cached'] += 1
            cached = self._cache[cache_key]
            return cached['translated'], cached.get('source_lang', source_lang)

        # Translate using local Ollama
        try:
            prompt = f"Translate the following text to English. Output ONLY the translated text, with no explanations, quotes, or additional text:\n\n{text}"
            
            response = ollama.generate(
                model=TRANSLATION_MODEL,
                prompt=prompt,
                options={'temperature': 0.1}  # Low temperature for deterministic translation
            )
            
            result = response.get('response', '').strip()
            
            if result and len(result) > 0:
                # Detect source language
                detected_lang = source_lang
                if not detected_lang:
                    try:
                        from langdetect import detect
                        detected_lang = detect(text)
                    except:
                        detected_lang = 'unknown'

                # Cache the result
                self._cache[cache_key] = {
                    'translated': result,
                    'source_lang': detected_lang,
                    'timestamp': datetime.now().isoformat()
                }
                self._stats['translated'] += 1

                # Save cache periodically (every 10 translations)
                if self._stats['translated'] % 10 == 0:
                    self._save_cache()

                return result, detected_lang
            else:
                raise Exception("Empty response from Ollama")
                
        except Exception as e:
            self._stats['failed'] += 1
            if self._stats['failed'] <= 3:
                print(f"    ⚠️  Local translation failed: {e}")
            # Fallback: return original text
            return text, source_lang or 'unknown'

    def translate_article(self, article, source_lang=None):
        """
        Translate a news article's title and summary.
        Returns new article dict with translated fields.
        """
        translated_article = article.copy()

        # Translate title
        original_title = article.get('title', '')
        translated_title, detected_lang = self.translate_text(original_title, source_lang)
        translated_article['title_translated'] = translated_title
        translated_article['title_original'] = original_title
        translated_article['detected_lang'] = detected_lang

        # Translate summary if present
        original_summary = article.get('summary', '')
        if original_summary:
            translated_summary, _ = self.translate_text(original_summary, detected_lang)
            translated_article['summary_translated'] = translated_summary
            translated_article['summary_original'] = original_summary
        else:
            translated_article['summary_translated'] = ''
            translated_article['summary_original'] = ''

        # Use translated text for main fields (for AI analysis)
        translated_article['title'] = translated_title
        translated_article['summary'] = translated_article.get('summary_translated', '')

        # Mark as translated
        translated_article['is_translated'] = (
            translated_title != original_title and
            detected_lang not in ['en', 'unknown']
        )
        translated_article['original_language'] = detected_lang

        return translated_article

    def get_stats(self):
        """Get translation statistics"""
        return self._stats.copy()

    def save_final_cache(self):
        """Save cache at end of session"""
        self._save_cache()
        print(f"    📊 Translation stats: {self._stats['translated']} new, {self._stats['cached']} cached, {self._stats['failed']} failed")

    # -----
    LANGUAGE_NAMES = LANGUAGE_NAMES

    def get_language_name(self, lang_code):
        """Convert language code to readable name"""
        return get_language_name(lang_code)