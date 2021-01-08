import re
import nltk
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords as nltk_stopwords

nltk.download('stopwords')

# expand this list later
lang_iso_dict = {"ar": "Arabic", "en": "English", "el": "Greek",
                 "pl": "Polish", "nl": "Dutch", "ru": "Russian",
                 "es": "Spanish", "de": "German", "da": "Danish",
                 "ro": "Romanian", "sk": "Slovak", "fr": "French",
                 "uk": "Ukrainian", "ja": "Japanese", "pt": "Portuguese",
                 "it": "Italian", "fa": "Persian", "zh": "Chinese"
                 }


class PreProc:
    def __init__(self, lang='en', stem=True, de_punctuate=True, de_stop=True, as_list=True, aggressive_de_punctuate=False):
        self.cache = {} # optionally saves processed texts by id for later retrieval
        self.lang = lang.lower()
        self.stem = stem
        self.de_punctuate = de_punctuate
        self.de_stop = de_stop
        self.as_list = as_list
        self.aggressive_de_punctuate = aggressive_de_punctuate
        self._full_lang = lang_iso_dict.get(lang, 'english').lower()
        self.stop_words = nltk_stopwords.words(self._full_lang)
        self.stemmer = SnowballStemmer(self._full_lang)

    def process_str_list(self, str_list):
        processed = []
        for str_item in str_list:
            processed.append(self.process_str(str_item))
        return processed

    def process_str(self, text, cache_id=None):
        if cache_id is not None:
            if cache_id in self.cache:
                return self.cache[cache_id]
        if self.de_punctuate:
            text = self._de_punctuate_func(text)
        result = self._tokenize_func(text)
        if self.as_list:
            if cache_id is not None:
                self.cache[cache_id] = result
            return result
        else:
            if cache_id is not None:
                self.cache[cache_id] = result
            return " ".join(result)

    def supported_langs(self):
        return ['en', 'fr', 'ar', 'de', 'es', 'el', 'pl', 'nl', 'ru', 'da', 'ro', 'sk', 'uk', 'pt', 'it', 'fa']

    def _stem_func(self, tokens):
        stemmed = []
        for item in tokens:
            stemmed.append(self.stemmer.stem(item))
        return stemmed

    def _tokenize_func(self, text):
        if self.de_stop:
            tokens = [token for token in nltk.word_tokenize(text) if token not in nltk_stopwords.words(self._full_lang)]
        else:
            tokens = nltk.word_tokenize(text)
        if self.stem:
            stems = self._stem_func(tokens)
            return stems
        else:
            return tokens

    def _de_punctuate_func(self, text, mid_punc_regex=r"[،,\.\'\";:؛]", add_space_before_regex=r"([!?؟])"):
        """
        Strip spaces around a sentence and remove punctuation and stop words.
        """
        just_rep_with_space = "-"
        text = re.sub(mid_punc_regex, "", text.lower().strip())
        text = re.sub(just_rep_with_space, " ", text)
        if self.aggressive_de_punctuate:
            text = re.sub(add_space_before_regex, "", text)
        else:
            text = re.sub(add_space_before_regex, r" \1", text)
        return text