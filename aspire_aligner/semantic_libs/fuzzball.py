import Levenshtein as py_lev
import re


class FuzzBall:
    def __init__(self, min_score_per_token=0.30, preprocess=True):
        self.min_score_per_token = min_score_per_token
        self.preprocess = preprocess

    def _find_scores(self, source_toks, target_toks):
        rated_pairs = []
        for source_tok in source_toks:
            for target_tok in target_toks:
                score = self._lev_tok_similarity(source_tok, target_tok)
                if score >= self.min_score_per_token:
                    rated_pairs.append(((source_tok, target_tok), score))
        return sorted(rated_pairs, key=lambda rated: rated[1], reverse=True)

    def _finalize_scores(self, sorted_scores):
        matches = []
        for scored_item in sorted_scores:
            source_tok = scored_item[0][0]
            target_tok = scored_item[0][1]
            # check if source or target are already in the list
            already_matched = True if len(
                [x for x in matches if x[0][0] == source_tok or x[0][1] == target_tok]) > 0 else False
            if not already_matched:
                matches.append(scored_item)
        return matches

    def _lev_tok_similarity(self, source_tok, target_tok):
        if len(source_tok) == 0 or len(target_tok) == 0:
            return 0
        return 1 - (py_lev.distance(source_tok, target_tok) / max([len(source_tok), len(target_tok)]))

    def _preprocess(self, sentence):
        sentence = sentence.lower().strip()
        punc_regex = r"[؟;:؛!?,\.\'\"\- ]+"  # todo: remove diacritics
        sentence = re.sub(punc_regex, " ", sentence)
        return sentence

    def lev_sentence_similarity(self, source_sentence, target_sentence):
        if len(source_sentence) == 0 or len(target_sentence) == 0:
            return 0

        # pre-process (only if preprocess is True and and provided sentences are strings. If provided sentences
        # are lists of words, it is assumed that they are processed tokens
        if self.preprocess and type(source_sentence) is str and type(target_sentence) is str:
            source_sentence = self._preprocess(source_sentence)
            target_sentence = self._preprocess(target_sentence)

        # tokenize by space if not tokenized already
        if type(source_sentence) is list:
            source_toks = set(source_sentence)
        else:
            source_toks = set(source_sentence.split())
        if type(target_sentence) is list:
            target_toks = set(target_sentence)
        else:
            target_toks = set(target_sentence.split())


        # check if any tokens are left after cleanup
        if len(source_toks) == 0 or len(target_toks) == 0:
            return 0

        # get all scores
        all_sorted_scores = self._find_scores(source_toks, target_toks)

        # finalize scores and settle conflicts
        final_scores = self._finalize_scores(all_sorted_scores)

        # math
        total = sum([val for (key, val) in final_scores])
        average = total / ((len(source_toks) + len(target_toks)) / 2)

        return average
