from .fuzzball import FuzzBall
from aspire_aligner.semantic_libs import preprocess
import re


class FuzzyComp:
    def __init__(self, options={}):

        if options.get('comp_lang_code', None) is None:
            raise Exception("FuzzBall requires comp_lang_code in options dictionary.")

        if options['comp_lang_code'] not in self.supported_langs():
            raise Exception("Language '{}' not supported by the FuzzyComp method.".format(options['comp_lang_code']))

        self.nlp_proc = preprocess.PreProc(options['comp_lang_code'], stem=False, de_punctuate=True, de_stop=True,
                                           aggressive_de_punctuate=False).process_str

    def alg_name(self):
        return 'FuzzBall'

    def supported_langs(self):
        return ['en', 'fr', 'ar', 'de', 'es', 'el', 'pl', 'nl', 'ru', 'da', 'ro', 'sk', 'uk', 'pt', 'it', 'fa']

    def requires_corpus(self):
        return False

    def comp_one(self, src_segment, tar_segment):
        fb = FuzzBall(0.7, preprocess=False)
        src_comp_toks = self.nlp_proc(src_segment.comp_text, cache_id="src_{}".format(src_segment.index))
        tar_comp_toks = self.nlp_proc(tar_segment.comp_text, cache_id="tar_{}".format(tar_segment.index))
        return fb.lev_sentence_similarity(src_comp_toks, tar_comp_toks)

    def comp_many(self, src_segments, tar_segments):
        fb = FuzzBall(0.7, preprocess=False)
        combined_src_comp_toks = []
        combined_tar_comp_toks = []
        for seg in src_segments:
            combined_src_comp_toks += self.nlp_proc(seg.comp_text)
        for seg in tar_segments:
            combined_tar_comp_toks += self.nlp_proc(seg.comp_text)
        return fb.lev_sentence_similarity(combined_src_comp_toks, combined_tar_comp_toks)

    def get_options(self):
        return {"location_weight": 0.2,
                "length_weight": 0.1,
                "semantic_weight": 0.5,
                "meta_weight": 0.2,
                "minimum_semantic_score": 0.4,
                "minimum_length_score": 0.5,
                "minimum_anchor_semantic_score": 0.7,
                "minimum_anchor_length_score": 0.7,
                "search_range": 20,
                "initial_leniency_multiplier": 0.2,
                "high_context_leniency_multiplier": 0.6,
                "minimum_partial_sem_match": 0.2
                }
