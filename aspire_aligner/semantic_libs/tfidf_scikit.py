import nltk
import re
from aspire_aligner.semantic_libs import preprocess
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem import SnowballStemmer

# from nltk.corpus import stopwords as nltk_stopwords

nltk.download('punkt')

# expand this list later
lang_iso_dict = {"ar": "Arabic", "en": "English", "el": "Greek",
                 "pl": "Polish", "nl": "Dutch", "ru": "Russian",
                 "es": "Spanish", "de": "German", "da": "Danish",
                 "ro": "Romanian", "sk": "Slovak", "fr": "French",
                 "uk": "Ukrainian", "ja": "Japanese", "pt": "Portuguese",
                 "it": "Italian", "fa": "Persian", "zh": "Chinese"
                 }


class TfidfComp:
    def __init__(self, options={}):
        self.vec_cache = {}
        self.options = options

        if options.get('comp_lang_code', None) is None:
            raise Exception("TfidfComp requires comp_lang_code in options dictionary.")

        if options['comp_lang_code'] not in self.supported_langs():
            raise Exception("Language '{}' not supported by the tfidf method.".format(options['comp_lang_code']))

        self.nlp_proc = preprocess.PreProc(options['comp_lang_code'], stem=True, de_punctuate=True,
                                           de_stop=False,
                                           aggressive_de_punctuate=False).process_str

        self._vectorizer = None
        self._vectorized_corpus = None

    def reset(self):
        self.vec_cache = {}
        self.options = {}


    def alg_name(self):
        return 'Tf-Idf - Scikit learn'

    def supported_langs(self):
        return ['en', 'fr', 'ar', 'de', 'es', 'el', 'pl', 'nl', 'ru', 'da', 'ro', 'sk', 'uk', 'pt', 'it', 'fa']

    def requires_corpus(self):
        return True

    def set_corpus(self, src_segments, tar_segments):
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 3), tokenizer=self.nlp_proc)
        if src_segments.has_mt:
            self._vectorized_corpus = self._vectorizer.fit_transform(src_segments.mt_strings)
        else:
            self._vectorized_corpus = self._vectorizer.fit_transform(src_segments.text_strings)

    def comp_one(self, src_segment, tar_segment):
        # src segments are already preprocessed and stored in self._vec_corpus
        # but check if tar segment's vectors are cached to speed processing
        tar_vec_cache_index = "tar_{}".format(tar_segment.index)
        if tar_vec_cache_index in self.vec_cache:
            query_vec2 = self.vec_cache[tar_vec_cache_index]
        else:
            query_vec2 = self._vectorizer.transform([tar_segment.comp_text])
            self.vec_cache[tar_vec_cache_index] = query_vec2

        query_vec1 = self._vectorized_corpus[src_segment.index]

        similarity_score = cosine_similarity(query_vec1, query_vec2)[0][0]
        return similarity_score

    def comp_many(self, src_segments, tar_segments):
        combined_src_comp_text = ''
        combined_tar_comp_text = ''
        for seg in src_segments:
            combined_src_comp_text += " " + seg.comp_text
        for seg in tar_segments:
            combined_tar_comp_text += " " + seg.comp_text

        # Obtain or store combined segments from cache
        src_vec_cache_index = "src_{}".format("_".join([str(seg.index) for seg in src_segments]))
        tar_vec_cache_index = "tar_{}".format("_".join([str(seg.index) for seg in tar_segments]))

        if src_vec_cache_index in self.vec_cache:
            query_vec1 = self.vec_cache[src_vec_cache_index]
        else:
            query_vec1 = self._vectorizer.transform([combined_src_comp_text])
            self.vec_cache[src_vec_cache_index] = query_vec1

        if tar_vec_cache_index in self.vec_cache:
            query_vec2 = self.vec_cache[tar_vec_cache_index]
        else:
            query_vec2 = self._vectorizer.transform([combined_tar_comp_text])
            self.vec_cache[tar_vec_cache_index] = query_vec2

        similarity_score = cosine_similarity(query_vec1, query_vec2)[0][0]
        return similarity_score

    def get_options(self):
        return {"location_weight": 0.2,
                "length_weight": 0.1,
                "semantic_weight": 0.6,
                "meta_weight": 0.1,
                "minimum_semantic_score": 0.3,
                "minimum_length_score": 0.6,
                "minimum_anchor_semantic_score": 0.5,
                "minimum_anchor_length_score": 0.6,
                "search_range": 20,
                "initial_leniency_multiplier": 0.1,
                "high_context_leniency_multiplier": 0.5,
                "minimum_partial_sem_match": 0.2
                }
