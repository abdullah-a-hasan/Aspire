import nltk
import re
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords
# from spacy.lang.en.stop_words import STOP_WORDS

nltk.download('punkt')

# expand this list later
lang_iso_dict = {"ar": "Arabic", "en": "English", "el": "Greek",
                 "pl": "Polish", "nl": "Dutch", "ru": "Russian",
                 "es": "Spanish", "de": "German", "da": "Danish",
                 "ro": "Romanian", "SK": "Slovak", "fr": "French",
                 "uk": "Ukrainian", "ja": "Japanese", "pt": "Portuguese",
                 "it": "Italian", "fa": "Persian", "zh": "Chinese"
                 }


class JaccardComp:
    def __init__(self, options={}):
        self.options = options

    def supported_langs(self):
        return ['en', 'fr', 'ar', 'de', 'es']

    def _dep_comp(self, string_1, string_2, lang):
        """
         Calculates the similarity between two sentences based on NLTK's jaccard_distance method.
         Sentences are stemmed first.
         """
        if lang not in self.supported_langs():
            raise Exception("Language '{}' not supported by the jaccard-based method.".format(lang))
        # get the full language name
        lang_full_name = lang_iso_dict.get(lang, '-').lower()  # converts lang iso code to full lang name or -
        # check if lang_full_name is supported by the stemmer
        if lang_full_name in SnowballStemmer.languages:
            # self._log("_jaccard_compare: stemming supported for {}".format(lang_full_name))
            stemmer = SnowballStemmer(lang_full_name)
            string_1 = self._deflate(string_1, stopwords.words('english')) # todo: set stopwords dynamically
            string_2 = self._deflate(string_2, stopwords.words('english'))
            string_1_toks = set(
                map(lambda word: stemmer.stem(word), nltk.word_tokenize(string_1)))
            string_2_toks = set(
                map(lambda word: stemmer.stem(word), nltk.word_tokenize(string_2)))
        else:
            # self._log("_jaccard_compare: stemming not supported for {}".format(lang_full_name))
            string_1_toks = nltk.word_tokenize(string_1)
            string_2_toks = nltk.word_tokenize(string_2)

        # distance is converted to a score
        # self._log("_jaccard_compare: tokenized and/or stemmed string_1:" + " | ".join(string_1_toks))
        # self._log("_jaccard_compare: tokenized and/or stemmed string_2:" + " | ".join(string_2_toks))

        similarity_score = 1 - nltk.jaccard_distance(string_1_toks, string_2_toks)
        return similarity_score
