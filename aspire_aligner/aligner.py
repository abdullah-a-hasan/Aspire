# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 13:39:12 2019
@author: blazi
"""
import datetime as dt
# env libs
import json
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET

import langdetect as lang_detect
from xlwt import Workbook, easyxf

import aspire_aligner.helpers as helpers

# import math
# import nltk
# import hashlib

# from aspire_aligner.semantic_libs.preprocess import PreProc

# initialize logging
global logging
# logging.raiseExceptions = True
logging.basicConfig(filename="aspire_aligner_lo.log", format='%(levelname)s: %(asctime)s: %(message)s',
                    filemode='w',
                    level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class Segment:
    """
    Class representing a segment.
    ...
    Attributes:
    -----------
    index : int
        the segments index
    text : str
        the segment's main text
    mt_text : str
        the segment's machine translation text, if any
    has_mt : bool
        whether or not machine translation is available for the segment
    """
    def __init__(self, index, text, mt_text, has_mt=False):
        self.index = index
        self.text = text
        self.mt_text = mt_text
        self.has_mt = has_mt
        self.comp_text = (self.mt_text if self.has_mt else self.text)

    def __len__(self):
        return len(self.mt_text) if self.has_mt else len(self.text)


class SegmentsList:
    def __init__(self, text_strings, mt_strings=[], text_lang_code='auto',
                 mt_lang_code='auto'):
        self.text_lang_code = text_lang_code  # TODO: auto detect lang if 'auto'
        self.mt_lang_code = mt_lang_code  # TODO: auto detect lang if 'auto'
        self.has_mt = (True if len(text_strings) == len(mt_strings) else False)
        self.text_strings = text_strings
        self.mt_strings = mt_strings
        # self._Segment = namedtuple('Segment', 'index text mt comp has_mt')

    def __getitem__(self, index):
        # set mt to corresponding mt item from the list or to none
        mt_text = (self.mt_strings[index] if self.has_mt else '')
        return Segment(index, self.text_strings[index], mt_text, self.has_mt)

    def __iter__(self):
        for index in range(len(self.text_strings)):
            # set mt to corresponding mt item from the list or to none
            mt_text = (self.mt_strings[index] if self.has_mt else '')
            yield Segment(index, self.text_strings[index], mt_text, self.has_mt)

    def __len__(self):
        return len(self.text_strings)


class TranslationAligner:
    def __init__(self):
        # begin init values
        self.src_strings = []
        self.tar_strings = []
        self.src_mt_strings = []
        self.tar_mt_strings = []
        self.src_lang_code = ''
        self.tar_lang_code = ''
        self.src_mt_lang_code = ''
        self.tar_mt_lang_code = ''
        self.src_segments = None
        self.tar_segments = None
        self.scores = []  # listofscores
        self.alignments = []  # ordereddictofalignments
        self.correlated_candidates = []
        self.comparison_algorithm = ""
        self.comp_lang_code = ""
        # end init values
        self._tar_highest_sem_scores = {}  # each tar index is linked with the highest semantic score it achieved for tracking. Useful for avoiding duplicates in one-to-many matches
        # self._tar_takers = {}  # each tar index is linked with src that had the highest average math with it
        self._taken_tars = []
        self.comp_obj = None

    def _set_options(self, options):
        """
        Use the provided options dictionary.
        """
        default_options = self.comp_obj.get_options()
        # set options
        self.location_weight = options.get("location_weight", default_options['location_weight'])
        self.length_weight = options.get("length_weight", default_options['length_weight'])
        self.semantic_weight = options.get("semantic_weight", default_options['semantic_weight'])
        self.meta_weight = options.get("meta_weight", default_options['meta_weight'])
        self.minimum_anchor_semantic_score = options.get("minimum_anchor_semantic_score",
                                                         default_options['minimum_anchor_semantic_score'])
        self.minimum_anchor_length_score = options.get("minimum_anchor_length_score",
                                                       default_options['minimum_anchor_length_score'])
        self.minimum_semantic_score = options.get("minimum_semantic_score", default_options['minimum_semantic_score'])
        self.minimum_length_score = options.get("minimum_length_score", default_options['minimum_length_score'])
        self.search_range = options.get("search_range", default_options['search_range'])
        self.initial_leniency_multiplier = options.get("initial_leniency_multiplier",
                                                       default_options['initial_leniency_multiplier'])
        self.high_context_leniency_multiplier = options.get("high_context_leniency_multiplier",
                                                            default_options['high_context_leniency_multiplier'])
        self.minimum_partial_sem_match = options.get("minimum_partial_sem_match",
                                                     default_options['minimum_partial_sem_match'])
        logging.info('_set_options: options were set to: %r', str(self._get_options()))

    def _get_options(self):
        """
        Gets the current options dictionary.
        """
        return {
            'location_weight': self.location_weight,
            'length_weight': self.length_weight,
            'semantic_weight': self.semantic_weight,
            'meta_weight': self.meta_weight,
            'minimum_anchor_semantic_score': self.minimum_anchor_semantic_score,
            'minimum_anchor_length_score': self.minimum_anchor_length_score,
            'minimum_semantic_score': self.minimum_semantic_score,
            'minimum_length_score': self.minimum_length_score,
            'search_range': self.search_range,
            'initial_leniency_multiplier': self.initial_leniency_multiplier,
            'high_context_leniency_multiplier': self.high_context_leniency_multiplier,
            'minimum_partial_sem_match': self.minimum_partial_sem_match
        }

    def _load_strings(self, src_strings, tar_strings, src_mt_strings=[], tar_mt_strings=[], src_lang_code='auto',
                      tar_lang_code='auto',
                      src_mt_lang_code='auto', tar_mt_lang_code='auto'):
        """
        Load strings into algorithm and detect and verify language codes.
        """
        if len(src_strings) == 0 or len(tar_strings) == 0:
            logging.exception("_load_strings: no strings were provided for either src or tar.")
            raise Exception('Required information missing.')

        if len(src_mt_strings) == 0 and len(tar_mt_strings) == 0:
            logging.exception("_load_strings: at least one MT list should be provided for src or tar.")
            raise Exception('Required information missing.')

        self.src_strings = src_strings
        self.tar_strings = tar_strings
        self.src_mt_strings = src_mt_strings
        self.tar_mt_strings = tar_mt_strings
        self.src_lang_code = lang_detect.detect(' '.join(src_strings)) if src_lang_code == 'auto' else src_lang_code
        self.tar_lang_code = lang_detect.detect(' '.join(tar_strings)) if tar_lang_code == 'auto' else tar_lang_code
        if len(src_mt_strings) > 0:
            self.src_mt_lang_code = lang_detect.detect(
                ' '.join(src_mt_strings)) if src_mt_lang_code == 'auto' else src_mt_lang_code
        else:
            self.src_mt_lang_code = ''
        if len(tar_mt_strings) > 0:
            self.tar_mt_lang_code = lang_detect.detect(
                ' '.join(tar_mt_strings)) if tar_mt_lang_code == 'auto' else tar_mt_lang_code
        else:
            self.tar_mt_lang_code = ''
        logging.info('_load_strings: language codes: src: %r, tar: %r, src_mt: %r, tar_mt:% r', self.src_lang_code, self.tar_lang_code,
                     self.src_mt_lang_code, self.tar_mt_lang_code)
        # Verify language selections
        if self.src_mt_lang_code != '' and self.tar_mt_lang_code != '':
            if self.src_mt_lang_code != self.tar_mt_lang_code:
                logging.error('_load_strings: Language mismatch between MT strings.')
                raise Exception("Language mismatch error.")
        elif self.src_mt_lang_code != '' and self.src_mt_lang_code != self.tar_lang_code:
            logging.error('_load_strings: Language mismatch between src MT strings and tar strings.')
            raise Exception("Language mismatch error.")
        elif self.tar_mt_lang_code != '' and self.tar_mt_lang_code != self.src_lang_code:
            logging.error('_load_strings: Language mismatch between tar MT strings and src strings.')
            raise Exception("Language mismatch error.")

        if self.src_mt_lang_code != '':
            self.comp_lang_code = self.src_mt_lang_code
        if self.tar_mt_lang_code != '':
            self.comp_lang_code = self.tar_mt_lang_code

        self.src_segments = SegmentsList(self.src_strings, self.src_mt_strings, self.src_lang_code, self.src_mt_lang_code)
        self.tar_segments = SegmentsList(self.tar_strings, self.tar_mt_strings, self.tar_lang_code, self.tar_mt_lang_code)

    def compare(self, src_indexes, tar_indexes):
        """
        Wrapper function that automatically calls the chosen algorithm's comparison functions: comp_one, or comp_many
        """
        if len(src_indexes) == 1 and len(tar_indexes) == 1:
            score = self.comp_obj.comp_one(self.src_segments[src_indexes[0]], self.tar_segments[tar_indexes[0]])
        elif len(src_indexes) > 1 or len(tar_indexes) > 1:
            combined_src_segments = [self.src_segments[i] for i in src_indexes]
            combined_tar_segments = [self.tar_segments[i] for i in tar_indexes]
            score = self.comp_obj.comp_many(combined_src_segments, combined_tar_segments)
        else:
            return 0
        return score

    def align(self, semantic_lib, src_strings, tar_strings, src_mt_strings=[], tar_mt_strings=[], options='auto'):
        """
        Aligns lists of strings representing segmented source and target texts. Requires at least one list of MT strings.
        Args:
            semantic_lib: instance of the semantic comparison library to use
            src_strings: list of source strings
            tar_strings: list of target strings
            src_mt_strings: list of MT strings of source strings
            tar_mt_strings: list of MT strings of target strings
            options: dictionary of options. Refer to options_sample.json. 'auto' will use the semantic library's defaults.
        """
        self._load_strings(src_strings, tar_strings, src_mt_strings,
                           tar_mt_strings)  # detects lang codes and sets self.src_segments and self.tar_segments
        self.comp_obj = semantic_lib(
            {'comp_lang_code': self.comp_lang_code})  # todo: verify the object meets requirements
        if options == 'auto':
            self._set_options(self.comp_obj.get_options())
            logging.info('align: default alignment options will be used.')
        else:
            self._set_options(options)
        if self.comp_obj.requires_corpus():
            logging.info('align: corpus was set.')
            self.comp_obj.set_corpus(self.src_segments, self.tar_segments)

        logging.info('align: phase 1; scoring segments and finding best matches.')
        self._score_phase1()
        logging.info('align: phase 2; scoring meta features.')
        self._score_phase2()
        logging.info('align: phase 3; binding one-to-one, one-to-many, and many-to-one pairs.')
        self._pair_phase3()
        logging.info('align: phase 4; finalizing.')
        self._finalize_phase4()

    def batch_align(self, semantic_lib, batch_dict, output_filename='alignments', input_dir='', output_dir='',
                    file_format='tmx', options='auto'):
        """
        Performs batch alignments. batch_dict format: [{'src':'file1', 'tar':'file2', 'src_mt':'file3', 'tar_mt':'file4'}]
        """
        row_num = 0
        for row in batch_dict:
            row_num += 1
            src_file = row.get('src', '')
            tar_file = row.get('tar', '')
            src_mt_file = row.get('src_mt', '')
            tar_mt_file = row.get('tar_mt', '')
            src_strings = []
            tar_strings = []
            src_mt_strings = []
            tar_mt_strings = []
            if not src_file or not tar_file:
                logging.warning('batch_align: src or tar missing from row %r. Row skipped.', row_num)
                continue
            if not src_mt_file and not tar_mt_file:
                logging.warning('batch_align: src_mt or tar_mt missing from row %r. Row skipped', row_num)
                continue
            src_file = os.path.join(input_dir, src_file)
            tar_file = os.path.join(input_dir, tar_file)
            if os.path.exists(src_file) and os.path.exists(tar_file):
                src_strings = helpers.file_to_list(src_file)
                tar_strings = helpers.file_to_list(tar_file)
            else:
                logging.warning('batch_align: src and/or tar files at row %r do not exist. Row skipped.',
                                row_num)
                continue

            src_mt_file = os.path.join(input_dir, src_mt_file)
            tar_mt_file = os.path.join(input_dir, tar_mt_file)

            if not os.path.exists(src_mt_file) and not os.path.exists(tar_mt_file):
                logging.warning(
                    'batch_align: src_mt file and tar_mt file at row %r do not exist. Row skipped.',
                    row_num)
                continue
            if os.path.exists(src_mt_file):
                src_mt_strings = helpers.file_to_list(src_mt_file)
            if os.path.exists(tar_mt_file):
                tar_mt_strings = helpers.file_to_list(tar_mt_file)

            if len(src_mt_strings) > 0 and len(src_strings) != len(src_mt_strings):
                logging.warning('batch_align: src and src_mt segment counts do not match at row %r. Row skipped.',
                                row_num)
                continue
            if len(tar_mt_strings) > 0 and len(tar_strings) != len(tar_mt_strings):
                logging.warning('batch_align: tar and tar_mt segment counts do not match at row %r. Row skipped.',
                                row_num)
                continue
            # align, export
            try:
                self.align(semantic_lib, src_strings, tar_strings, src_mt_strings, tar_mt_strings, options)
            except Exception as e:
                logging.error(
                    'batch_align: error while running the align function for files at row %r. Row skipped. Details: %r',
                    row_num, str(e))
                continue
            if file_format == 'json':
                fname = "{}_{}.json".format(output_filename, row_num)
                self.export_json_dict(os.path.join(output_dir, fname))
            elif file_format == 'tmx':
                json_dict = self.export_json_dict()
                fname = "{}_{}.tmx".format(output_filename, row_num)
                self.export_tmx(os.path.join(output_dir, fname), json_dict)
            elif file_format == 'xls':
                json_dict = self.export_json_dict()
                fname = "{}_{}.xls".format(output_filename, row_num)
                self.export_excel(os.path.join(output_dir, fname), json_dict)
            elif file_format == 'xls_verbose':
                json_dict = self.export_json_dict()
                fname = "{}_{}.xls".format(output_filename, row_num)
                self.export_excel_verbose(os.path.join(output_dir, fname), json_dict)
            # reset
            self.reset()

        logging.info('batch_align: finished batch processing.')

    def reset(self):
        logging.info('rest: resetting aligner.')
        self.__init__()

    def _score_phase1(self):
        """
        Pairs the indexes of each source segment with the top matching target segments based on
        semantic similarity, length, and location anchors.
        """
        # prepare alignment candidates
        sort_by = "avg"  # avg is the weighted average score. Possible values: avg, sem, len, loc
        self.scores = []  # reset existing alignments from previous calls # todo: convert to session based
        # create anchors (anchors are segments that get high scores, which are then used to calculate a better location score for subsequent segments)
        left_anchor = -1
        right_anchor = -1
        last_anchor_sem_score = 0
        look_for_new_anchor = True
        for src_index, src_segment in enumerate(self.src_segments):
            #print("Progress: {x}/{y}.".format(x=src_index + 1, y=len(self.src_segments)))
            if src_segment.comp_text == '':  # checks if left segment is empty
                self.scores.append({"src_index": src_index, "is_anchor": False,
                                    "is_translatable": self._is_translatable(self.src_segments[src_index].text),
                                    "top_matches": []})
            else:  # src segment is not empty, proceed to look for matches in tar
                matched_tar_items = []
                # generate then loop through anchor-based candidates
                for candidate_index in self._gen_anchor_based_candidates(src_index, left_anchor, right_anchor,
                                                                         len(self.tar_segments)):

                    if self.tar_segments[candidate_index].comp_text == '':  # skip empty tar segments
                        continue
                    candidate_len_closeness = self._length_score(src_segment.comp_text,
                                                                 self.tar_segments[candidate_index].comp_text)
                    # in light/fast mode, skip this tar if len_closeness is too low
                    # semantic_similarity_score = self.compare(self.src_segments[src_index], self.tar_segments[candidate_index])
                    semantic_similarity_score = self.compare([src_index], [candidate_index])
                    # find anchored location similarity
                    acnhored_score = self._anchored_location_score(src_index, candidate_index, left_anchor, right_anchor)

                    # average_score = sum([candidate_len_closeness * self.length_weight, semantic_similarity_score * self.semantic_weight, candidate_loc_closeness * self.location_weight])
                    average_score = sum(
                        [candidate_len_closeness * self.length_weight, semantic_similarity_score * self.semantic_weight,
                         acnhored_score * self.location_weight])
                    # Now create a target item containing all the rating info
                    candidate_scores = {"avg": average_score, "sem": semantic_similarity_score,
                                        "len": candidate_len_closeness, "loc": acnhored_score}
                    tar_item = {"tar_index": candidate_index, "scores": candidate_scores}
                    matched_tar_items.append(tar_item)

                # sort matches by average
                # sorted_tar_matches = sorted(matched_tar_items.items(), key=lambda key_val: key_val[1]["scores"]["avg"], reverse=True)[:50]
                # top_tar_matches = dict(sorted_tar_matches)
                top_tar_matches = sorted(matched_tar_items, key=lambda item: item["scores"]["avg"], reverse=True)[:50]

                # if any matches are found at all, mark anchors if any, then link matches to src segment
                if len(matched_tar_items) > 0:  # if 0, then no good matches were found above "minimum_semantic_score"
                    # set new anchors if semantic and length similarity is higher than a specific score, higher than the
                    # last semantic score, and the segment is long enough
                    is_anchor = False
                    # top_tar_key = self._top_dict_key(top_tar_matches)
                    # if the top item match does not have a 1.00 loc score or an above minimum semantic score, decide to look for a new anchor by setting last_anchor_sem_score to 0
                    if top_tar_matches[0]["scores"]["loc"] < 1 or \
                            top_tar_matches[0]["scores"]["sem"] < self.minimum_semantic_score:
                        # last_anchor_sem_score = 0  # this will force looking for new anchors (which should still meet other criteria)
                        look_for_new_anchor = True
                    if top_tar_matches[0]["scores"]["sem"] >= self.minimum_anchor_semantic_score and \
                            (look_for_new_anchor is True or top_tar_matches[0]["scores"][
                                "sem"] > last_anchor_sem_score) and \
                            top_tar_matches[0]["scores"]["len"] > self.minimum_anchor_length_score and \
                            len(self.src_segments[src_index].comp_text) > 25:
                        left_anchor = src_index
                        right_anchor = top_tar_matches[0]['tar_index']
                        last_anchor_sem_score = top_tar_matches[0]["scores"]["sem"]
                        is_anchor = True
                        look_for_new_anchor = False  # we're good for now unless things start to look fishy
                        # calculate meta scores by looping over top_matches
                    self.scores.append({"src_index": src_index,
                                        "is_anchor": is_anchor,
                                        "is_translatable": self._is_translatable(self.src_segments[src_index].text),
                                        "top_matches": top_tar_matches})

        return self.scores

    def _score_phase2(self):
        """
        Calculate meta scores for special tokens and context, and re-calculates average.
        """
        for src_item in self.scores:
            current_loc_score = 0
            prev_loc_score = 0
            next_loc_score = 0
            prev_len_score = 0
            next_len_score = 0
            prev_sem_score = 0
            next_sem_score = 0
            # get current loc score only if there are matches
            if len(src_item['top_matches']) == 0:
                continue  # no matches
            src_index = src_item['src_index']
            for tar_item in src_item['top_matches']:
                tar_index = tar_item['tar_index']
                current_loc_score = tar_item['scores']['loc']
                len_score = tar_item['scores']['len']
                # get loc score of previous segment unless current segment is 0
                if src_index > 0:
                    if len(self.scores[src_index - 1]['top_matches']) > 0:
                        prev_top_matches = self.scores[src_index - 1]['top_matches']
                        prev_loc_score = prev_top_matches[0]['scores']['loc']
                        prev_len_score = prev_top_matches[0]['scores']['len']
                        prev_sem_score = prev_top_matches[0]['scores']['sem']
                # get loc score of next segment unless the current segment is the last one
                if src_index + 1 < len(self.scores):
                    if len(self.scores[src_index + 1]['top_matches']) > 0:
                        next_top_matches = self.scores[src_index + 1]['top_matches']
                        next_loc_score = next_top_matches[0]['scores']['loc']
                        next_len_score = next_top_matches[0]['scores']['len']
                        next_sem_score = next_top_matches[0]['scores']['sem']
                meta_score = self._meta_score(text1=self.src_segments[src_index].comp_text,
                                              text2=self.tar_segments[tar_index].comp_text,
                                              len_score=len_score, prev_loc_score=prev_loc_score,
                                              current_loc_score=current_loc_score, next_loc_score=next_loc_score,
                                              prev_len_score=prev_len_score, next_len_score=next_len_score,
                                              prev_sem_score=prev_sem_score, next_sem_score=next_sem_score)
                # add meta score to other scores
                tar_item['scores']['meta'] = meta_score
                # re-calc a new weighted average that takes meta scores into account
                average_score = sum(
                    [tar_item['scores']['len'] * self.length_weight, tar_item['scores']['sem'] * self.semantic_weight,
                     tar_item['scores']['loc'] * self.location_weight, meta_score * self.meta_weight])
                tar_item['scores']['avg'] = average_score
                # keep track of highest sem (should do avg instead?) scores achieved per tar candidate. This is useful for avoiding conflicts in one-to-many matchings in phase 3
                if self._tar_highest_sem_scores.get(tar_index, {}).get('sem', 0) < tar_item['scores']['sem']:
                    self._tar_highest_sem_scores.update(
                        {tar_index: {'sem': tar_item['scores']['sem'], 'src_index': src_index}})
            # resort by the new average
            src_item['top_matches'] = sorted(src_item['top_matches'], key=lambda item: item["scores"]["avg"],
                                            reverse=True)
            # add top tar_index to taken_tars
            if len(src_item['top_matches']) > 1:
                top_tar_index = src_item['top_matches'][0]['tar_index']
                self._taken_tars.append(top_tar_index)

    def _pair_phase3(self):
        """
        Pairs scored segments based on scores, establishing one-to-one, one-to-many, and many-to-one alignments.
        """
        for src_index, src_item in enumerate(self.scores):
            if len(src_item['top_matches']) == 0 or src_item['is_translatable'] is False:
                continue
            # last_sem_score = 0

            top_tar_index_sem = src_item['top_matches'][0]['scores']['sem']
            top_tar_index_len = src_item['top_matches'][0]['scores']['len']
            top_tar_index = src_item['top_matches'][0]['tar_index']

            # determine many-to-one relations, check if previous src is top-matched with the same tar
            if src_index != 0:
                if len(self.scores[src_index - 1]['top_matches']) > 0 and self.scores[src_index - 1]['is_translatable']:
                    prev_src_top_match = self.scores[src_index - 1]['top_matches'][0]
                    # does previous src segment have the same tar match as current segment, and does its sem value meet requirements
                    if prev_src_top_match['tar_index'] == top_tar_index:
                        if self.minimum_partial_sem_match < prev_src_top_match['scores']['sem'] < 0.9:
                            if self._merged_src_len_acceptable(self.alignments[-1]['src_indexes'] + [src_index],
                                                              [top_tar_index]):
                                # check if merging improves sem score
                                if top_tar_index_sem >= self.minimum_partial_sem_match or self._does_merging_raise_sem(
                                        self.alignments[-1]['src_indexes'] + [src_index], [top_tar_index],
                                        prev_src_top_match['scores']['sem']):
                                    self.alignments[-1]['src_indexes'].append(src_index)
                                    continue

            # perform one-to-one at first,
            # then determine one-to-many relations
            # extract first, second, and third match indexes, if any, to see if they meet one-to-many criteria
            tar_indexes = []
            # we are initially lenient with scores because we may need to include low scoring items which may later make up higher scores when combined in many-to-one matches
            tar_indexes.append(top_tar_index)
            tar_indexes += self._one_to_many_look_around(src_index, top_tar_index, src_item['top_matches'],
                                                        direction='up', steps=4)
            tar_indexes += self._one_to_many_look_around(src_index, top_tar_index, src_item['top_matches'],
                                                        direction='down', steps=4)
            self.alignments.append({'src_indexes': [src_index], 'tar_indexes': sorted(tar_indexes)})

    def _finalize_phase4(self):
        """
        Gives pairs 'p' for 'pass' and 'f' for 'fail' based on minimum requirements provided in option.
        """
        for pair in self.alignments:
            if len(pair['tar_indexes']) == 0:
                pair['len'] = 0
                pair['sem'] = 0
                pair['verdict'] = 'f'
                continue
            # for one-to-one relations, fetch scores from self.scores
            if len(pair['src_indexes']) == 1 and len(pair['tar_indexes']) == 1:
                src_item = self.scores[pair['src_indexes'][0]]
                pair['len'] = src_item['top_matches'][0]['scores']['len']
                pair['sem'] = src_item['top_matches'][0]['scores']['sem']
                if src_item['top_matches'][0]['scores']['sem'] >= self.minimum_semantic_score and \
                        src_item['top_matches'][0]['scores']['len'] >= self.minimum_length_score:
                    pair['verdict'] = 'p'
                # for items having a 1.0 loc score and are preceded by a 0.25 meta score or higher, show some leniency
                elif src_item['top_matches'][0]['scores'][
                    'sem'] >= self.minimum_semantic_score * self.high_context_leniency_multiplier and \
                        src_item['top_matches'][0]['scores']['len'] >= self.minimum_length_score and \
                        src_item['top_matches'][0]['scores']['loc'] == 1 and \
                        src_item['top_matches'][0]['scores']['meta'] >= 0.25:
                    pair['verdict'] = 'p'
                    pair['elevated'] = 'yes'
                else:
                    pair['verdict'] = 'f'
            # for many-to-one or one-to-many relations, calc sem and len scores
            if len(pair['src_indexes']) > 1 or len(pair['tar_indexes']) > 1:
                comp1_text = " ".join([self.src_segments[i].comp_text for i in pair['src_indexes']])
                comp2_text = " ".join([self.tar_segments[i].comp_text for i in pair['tar_indexes']])
                len_score = self._length_score(comp1_text, comp2_text)
                sem_score = self.compare(pair['src_indexes'], pair['tar_indexes'])
                pair['len'] = len_score
                pair['sem'] = sem_score
                if len_score < self.minimum_length_score:
                    pair['verdict'] = 'f'
                    continue
                pair['verdict'] = 'p' if sem_score >= self.minimum_semantic_score else 'f'
        #print("Pairs:")
        #print(self.alignments)
        #print("highest scores", self._tar_highest_sem_scores)

    def export_json_dict(self, json_file=''):
        """
        Get alignment results, including scores and final pairs.
        Args:
            json_file: Optional. A json file to store alignment results.
        Returns:
            dict
        """
        options_dict = self._get_options()
        raw_text = {"src_strings": self.src_strings, "src_mt_strings": self.src_mt_strings, "tar_strings": self.tar_strings,
                    "tar_mt_strings": self.tar_mt_strings}
        meta = {'aligner-version': '0.03a',
                'source_language': self.src_lang_code,
                'target_language': self.tar_lang_code,
                'source_mt_language': self.src_mt_lang_code,
                'target_mt_language': self.tar_mt_lang_code,
                'algorithm': self.comp_obj.alg_name(),
                'options': options_dict}
        json_data = {'meta': meta, 'scores': self.scores, 'alignments': self.alignments, "raw_text": raw_text}
        if len(json_file) > 0:
            with open(json_file, 'w') as outfile:
                json.dump(json_data, outfile)
            logging.info('export_json_dict: alignments were exported to: %r', json_file)
        return json_data

    @staticmethod
    def export_tmx(tmx_file, results_dict, flip=False):
        """
        Exports alignment results to a TMX file.
        Args:
            tmx_file: TMX file to save results.
            results_dict: Results obtained from export_json_dict.
            flip: Whether to flip the language direction.
        """
        tool_name = 'Aspire Alignment Tool'
        time_info = dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        tree = ET.Element('tmx', {'version': '1.4'})
        ET.SubElement(tree, 'header',
                      {'adminlang': 'EN', 'creationtool': tool_name,
                       'creationtoolversion': results_dict['meta']['aligner-version'], 'segtype': 'sentence',
                       'srclang': results_dict['meta']['source_language' if not flip else 'target_language'],
                       'datatype': "unknown", 'creationdate': time_info})
        body = ET.SubElement(tree, 'body')
        src_strings = results_dict['raw_text']['src_strings']
        tar_strings = results_dict['raw_text']['tar_strings']
        for src_index, pair in enumerate(results_dict['alignments']):
            if len(pair['tar_indexes']) == 0:
                continue
            if pair['verdict'] != 'p':  # is fail
                continue
            tu = ET.SubElement(body, 'tu', {'creationdate': time_info, 'creationtool': tool_name})
            tuv_src = ET.SubElement(tu, 'tuv', {'xml:lang': results_dict['meta']['source_language']})
            tuv_tar = ET.SubElement(tu, 'tuv', {'xml:lang': results_dict['meta']['target_language']})
            ET.SubElement(tuv_src, 'seg').text = TranslationAligner._join_strs_by_indexes(pair['src_indexes'],
                                                                                          src_strings)
            ET.SubElement(tuv_tar, 'seg').text = TranslationAligner._join_strs_by_indexes(pair['tar_indexes'],
                                                                                          tar_strings)

        # create a new XML file with the results
        with open(tmx_file, 'wb') as fh:
            ET.ElementTree(tree).write(fh, encoding='utf-8', xml_declaration=True)

        logging.info('export_tmx: alignments were exported to: %r', tmx_file)

    @staticmethod
    def export_excel_verbose(excel_file, results_dict):
        """
        Generates a verbose alignment sheet in Excel format with source, target, scores, and other information
        useful for analyzing results.
        Args:
            excel_file: Excel file where alignment results will be saved.
            results_dict: Results obtained from export_json_dict.
        """
        wb = Workbook()
        merged_style = easyxf('pattern: pattern solid, fore_colour pale_blue;')
        plain_style = easyxf('pattern: pattern solid, fore_colour white;')
        sheet1 = wb.add_sheet('alignments')
        sheet1.write(0, 0, 's_index')
        sheet1.write(0, 1, 'source')
        sheet1.write(0, 2, 't_index')
        sheet1.write(0, 3, 'target')
        sheet1.write(0, 4, 'mt')
        sheet1.write(0, 5, 'sem')
        sheet1.write(0, 6, 'len')
        sheet1.write(0, 7, 'elevated')
        sheet1.write(0, 8, 'verdict')
        row = 1
        src_strings = results_dict['raw_text']['src_strings']
        tar_strings = results_dict['raw_text']['tar_strings']
        src_mt_strings = results_dict['raw_text']['src_mt_strings']
        tar_mt_strings = results_dict['raw_text']['tar_mt_strings']
        for index, pair in enumerate(results_dict['alignments']):
            # print("Excel writing:", index)
            # if len(pair['tar_indexes']) == 0:
            #    continue
            style = None
            if len(pair['src_indexes']) > 1 or len(pair['tar_indexes']) > 1:
                style = merged_style
            else:
                style = plain_style
            sheet1.write(row, 0, ",".join([str(i) for i in pair['src_indexes']]), style)  # s_index
            sheet1.write(row, 1, TranslationAligner._join_strs_by_indexes(pair['src_indexes'], src_strings),
                         style)  # source
            sheet1.write(row, 2, ",".join([str(i) for i in pair['tar_indexes']]), style)  # t_index
            sheet1.write(row, 3, TranslationAligner._join_strs_by_indexes(pair['tar_indexes'], tar_strings),
                         style)  # target
            if len(src_mt_strings) > 0:
                sheet1.write(row, 4, TranslationAligner._join_strs_by_indexes(pair['src_indexes'], src_mt_strings),
                             style)  # mt
            elif len(tar_mt_strings) > 0:
                sheet1.write(row, 4, TranslationAligner._join_strs_by_indexes(pair['tar_indexes'], tar_mt_strings),
                             style)  # mt
            sheet1.write(row, 5, pair['sem'], style)
            sheet1.write(row, 6, pair['len'], style)
            sheet1.write(row, 7, pair.get('elevated', 'no'), style)
            sheet1.write(row, 8, pair['verdict'], style)
            row += 1

        wb.save(excel_file)
        logging.info('export_excel_verbose: alignments were exported to: %r', excel_file)

    @staticmethod
    def export_excel(excel_file, results_dict):
        """
        Generates a sample alignment sheet in Excel format with two columns: source, and target
        Args:
            excel_file: Excel file where alignment results will be saved.
            results_dict: Results obtained from export_json_dict.
        """
        wb = Workbook()
        merged_style = easyxf('pattern: pattern solid, fore_colour pale_blue;')
        plain_style = easyxf('pattern: pattern solid, fore_colour white;')
        sheet1 = wb.add_sheet('alignments')
        sheet1.write(0, 0, 'source')
        sheet1.write(0, 1, 'target')
        row = 1
        src_strings = results_dict['raw_text']['src_strings']
        tar_strings = results_dict['raw_text']['tar_strings']
        for index, pair in enumerate(results_dict['alignments']):
            # print("Excel writing:", index)
            if len(pair['tar_indexes']) == 0:
                continue
            if pair['verdict'] != 'p':  # is fail
                continue
            style = None
            if len(pair['src_indexes']) > 1 or len(pair['tar_indexes']) > 1:
                style = merged_style
            else:
                style = plain_style
            sheet1.write(row, 0, TranslationAligner._join_strs_by_indexes(pair['src_indexes'], src_strings), style)
            sheet1.write(row, 1, TranslationAligner._join_strs_by_indexes(pair['tar_indexes'], tar_strings), style)
            row += 1

        wb.save(excel_file)
        logging.info('export_excel: alignments were exported to: %r', excel_file)

    # ---------auxiliary private functions----------------#

    def _is_translatable(self, text):
        """
        Returns false if the text is unsuitable for translation, like number-only segements.
        """
        if len(text) == 0:
            return False
        rules = {}
        rules['non-alpha'] = r"^[0-9\.\-\\\^\&\s\{\}\?\(\)\[\]:=+،,_/~@#`'\"$%<>!*]+$"
        rules['roman-nums'] = r"^[ ]*[ixvIXV]+[\.\- \: ]*$"

        for key in rules:
            if re.fullmatch(rules[key], text) is not None:
                return False

        return True

    def _length_score(self, param1, param2):
        '''
        Computes the a length score.Parameters can be integers or strings.
        '''
        len1 = 0
        len2 = 0
        if type(param1) is str:
            len1 = len(param1)
        elif type(param1) is int:
            len1 = param1

        if type(param2) is str:
            len2 = len(param2)
        elif type(param2) is int:
            len2 = param2

        # return 1 - (abs(len(source_sentence) - len(target_sentence)) / max(len(source_sentence), len(target_sentence)))
        min_val = min(len1, len2)
        max_val = max(len1, len2)
        if min_val == 0 or max_val == 0:
            return 0
        return min_val / max_val

    def _meta_score(self, text1, text2, len_score, prev_loc_score, current_loc_score, next_loc_score, prev_len_score,
                    next_len_score, prev_sem_score, next_sem_score):
        # weights
        special_toks_weight = 0.7
        in_context_weight = 0.3

        # init scores
        in_context_score = 0
        special_toks_score = 0

        # calculate in-context score
        # if len score is low, in_context_score will be 0 regardless of surrounding loc scores
        # if all scores are 1.0, in context score is 1.0
        if len_score < self.minimum_length_score or \
                prev_len_score < self.minimum_length_score or \
                prev_sem_score < self.minimum_semantic_score * self.high_context_leniency_multiplier:
            in_context_weight = in_context_weight / 3  # blunt the importance of in context weight if len is low
        if next_len_score < self.minimum_length_score or \
                next_sem_score < self.minimum_semantic_score * self.high_context_leniency_multiplier:
            in_context_weight = in_context_weight / 3  # blunt even further

        if current_loc_score == 1 and prev_loc_score == 1 and next_loc_score == 1:
            in_context_score = 1
        elif current_loc_score == 1 and (prev_loc_score == 1 or next_loc_score == 1):
            in_context_score = 0.75
        elif current_loc_score == prev_loc_score:
            in_context_score = 0.5

        # print("in_context_score:", in_context_score)

        # extract & compare special tokens overlap
        special_toks1 = self._extract_special_tokens(text1)
        special_toks2 = self._extract_special_tokens(text2)
        special_toks_score = self._lists_overlap_score(special_toks1, special_toks2)

        meta_score = (special_toks_score * special_toks_weight) + (in_context_score * in_context_weight)

        return meta_score

    def _anchored_location_score(self, left_pos, right_pos, left_anchor, right_anchor, pos_cost=5):
        distance = abs((right_pos - right_anchor) - (left_pos - left_anchor))
        weighted = (distance * pos_cost) / 100
        sim = 1 - weighted
        return sim

    def _gen_anchor_based_candidates(self, left_position, left_anchor, right_anchor, tar_segments_count, extend_by=20):
        # formula: point = right_anchor + left)
        left_distance = left_position - left_anchor
        point = right_anchor + left_distance

        start = point - extend_by
        end = point + extend_by + 1

        # trim start and end
        start = max([0, start])
        end = min([end, tar_segments_count])

        return range(start, end)

    def _lists_overlap_score(self, list1, list2):
        if len(list1) == 0 or len(list2) == 0:
            return 0
        overlap = list(set(list1) & set(list2))
        # print(overlap)
        overlap_len = len(overlap)
        return overlap_len / max([len(list1), len(list2)])

    def _extract_special_tokens(self, text):
        """
        Extracts a list of numbers, roman numerals, emails, urls, and special symbols found in the provided string.
        """
        rules = {}
        rules['acronyms'] = r"\b[A-Z]{2,}\b"  # this will also apply to roman numerals
        rules[
            'arabic_nums'] = r"\b[0-9]+[\.,\-0-9]*[0-9]+\b"  # numbers, can be with floating points, commas, or hyphens in the middle
        rules['emails'] = r"\S+@\S+"
        rules[
            'urls'] = r"(?i)\b(?:(?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\))+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        rules['end_punct'] = r"[\?!:;]{1}$"  # ? or @ or  ; or : at the end of the line
        rules[
            'alpha_bullets'] = r"^[A-Z]{1}[ \t]*[\.\-]"  # matches ordered list points followed by period or hyphen. E.g. "A." "B ." "C -"

        collect = []

        for key in rules:
            matches = re.findall(rules[key], text, re.M)
            # print(matches)
            # print(len(matches))
            if len(matches) > 0:
                collect.extend(matches)
        return collect

    def _top_dict_key(self, dict_data):
        # return list(dict_data.keys())[0]
        # return list(dict_data)[0:1][0]
        key = next(iter(dict_data))
        return key

    @staticmethod
    def _join_strs_by_indexes(indexes_list, strings_list):
        """
        Takes one or more indexes in indexes_list and finds and joins their corresponding strings from strings_list.
        Args:
            indexes_list: list of indexes
            strings_list: list of strings
        Returns:
        str
        """
        if len(indexes_list) == 0 or len(strings_list) == 0:
            return ""
        return " ".join([strings_list[index] for index in indexes_list])

    def _tar_item_scores_by_tar_index(self, tar_index, matches):
        # returns tar scores by tar index from the given matches (scores)
        for item in matches:
            if item['tar_index'] == tar_index:
                return item
        return None

    def _merged_src_len_acceptable(self, src_indexes, tar_indexes):
        # determines if tar is a good candidate for many-to-one and one-to-many merging based
        # on whether it breaks tar breaks len restrictions
        # get len of all src indexes
        str1 = " ".join([self.src_segments[i].comp_text for i in src_indexes])
        str2 = " ".join([self.tar_segments[i].comp_text for i in tar_indexes])
        if len(str1) / len(str2) > 1 / self.minimum_length_score:
            return False
        else:
            return True

    def _merged_tar_len_acceptable(self, src_indexes, tar_indexes):
        # determines if tar is a good candidate for many-to-one and one-to-many merging based
        # on whether it breaks tar breaks len restrictions
        # get len of all src indexes
        str1 = " ".join([self.src_segments[i].comp_text for i in src_indexes])
        str2 = " ".join([self.tar_segments[i].comp_text for i in tar_indexes])
        if len(str2) / len(str1) > 1 / self.minimum_length_score:
            return False
        else:
            return True

    def _is_src_highest_sem_among_neighbors(self, src_index, tar_index, sem):
        steps = 1  # how far to look backward and forward
        start = max([0, src_index - steps])
        end = min([src_index + steps, len(self.scores) - 1])
        loop = list(range(start, end + 1))
        loop.pop(loop.index(src_index))
        for i in loop:
            # if this src already has its own high match, ignore it and don't even compare with it
            # self.scores[index]['top_matches'][0]['scores']['sem']
            src_top_match = self._src_top_tar_match_by_index(i)
            if src_top_match:
                if src_top_match['scores']['sem'] >= self.minimum_semantic_score and \
                        src_top_match['scores']['len'] >= self.minimum_length_score:
                    continue
            tar_match = self._tar_item_scores_by_tar_index(tar_index, self.scores[i]['top_matches'])
            if tar_match:
                if tar_match['scores']['sem'] >= sem:
                    return False
        return True

    def _src_top_tar_match_by_index(self, src_index):
        if len(self.scores[src_index]['top_matches']) > 0:
            return self.scores[src_index]['top_matches'][0]
        else:
            return False

    def _does_merging_raise_sem(self, src_indexes, tar_indexes, original_sem):
        new_sem = self.compare(src_indexes, tar_indexes)
        if new_sem > original_sem:
            return True
        else:
            return False

    def _one_to_many_look_around(self, src_index, top_tar_index, tar_top_matches, direction='up', steps=4):
        """
        Looks around for partial matches.
        """
        # they have to come immediately after and before the current tar, and have at least 20% semantic match with src (todo: make the match a variable)
        # check up to three (forward and backward) additional consecutive tar matches but stop at the first failure
        # do not start before or at the tar match of the previous src

        tar_indexes = []
        if direction == 'down':
            starting_tar = top_tar_index + 1
            ending_tar = starting_tar + steps
            loop_tar_indexes = list(range(starting_tar, ending_tar))
        elif direction == 'up':
            ending_tar = top_tar_index
            starting_tar = ending_tar - steps
            loop_tar_indexes = reversed(list(range(starting_tar, ending_tar)))
        for potential_tar_index in loop_tar_indexes:  # range(-3, 4):
            potential_tar_item_scores = self._tar_item_scores_by_tar_index(potential_tar_index, tar_top_matches)
            # is this surrounding tar even among the matches
            if potential_tar_item_scores is None:
                return tar_indexes  # no need to continue. One disruption is enough
            # does it meet semantic criteria (like not having a higher match somewhere else)
            # items with between minimum_partial_sem_match and 0.9 similarity unlikely to be partial matches
            # if potential_tar_item_scores['scores']['sem'] >= self._tar_highest_sem_scores.get(ct, {}).get('sem', 0) and \
            potential_tar_indexes_combo = sorted([top_tar_index] + tar_indexes + [potential_tar_index])
            if self.minimum_partial_sem_match <= potential_tar_item_scores['scores']['sem'] < 0.9 and \
                    0.1 < potential_tar_item_scores['scores']['len'] < 0.9 and \
                    potential_tar_index not in self._taken_tars and \
                    self._merged_tar_len_acceptable([src_index], potential_tar_indexes_combo) and \
                    self._is_src_highest_sem_among_neighbors(src_index, potential_tar_index,
                                                            potential_tar_item_scores['scores']['sem']) and \
                    self._does_merging_raise_sem([src_index], potential_tar_indexes_combo,
                                                 tar_top_matches[0]['scores']['sem']):
                tar_indexes.append(potential_tar_index)
            else:
                return tar_indexes  # no need to continue. One disruption is enough
        return tar_indexes


# static
def test_accuracy(reference_src, reference_tar, aligned_src, aligned_tar, penalty_points=None):
    """
    Tests aligned lists of strings against reference lists, typically hand aligned.
    Args:
        reference_src: list of reference source strings
        reference_tar: list of reference target strings
        aligned_src: list of auto-aligned source strings
        aligned_tar: list of auto-aligned target strings
        penalty_points: dict of error types and penalty points. Default is {'bad': 1, 'noise': 1, 'missed': 1}

    Returns: dict
    """
    if penalty_points is None:
        penalty_points = {'bad': 1, 'noise': 1, 'missed': 1}
    if not (isinstance(reference_src, list) and
            isinstance(reference_tar, list) and
            isinstance(aligned_src, list) and
            isinstance(aligned_tar, list)):
        raise Exception("Expecting reference_src, reference_tar, aligned_src, and aligned_tar to be of type list.")
    if len(reference_src) != len(reference_tar):
        raise Exception(
            "Expecting reference_src and reference_tar to have the same length")
    if len(aligned_src) != len(aligned_tar):
        raise Exception(
            "Expecting aligned_src and aligned_tar to have the same length")

    reference_src = [item.lower().strip() for item in reference_src]
    reference_tar = [item.lower().strip() for item in reference_tar]
    aligned_src = [item.lower().strip() for item in aligned_src]
    aligned_tar = [item.lower().strip() for item in aligned_tar]

    # find mismatches. Penalize by 1 point per mismatch
    bad = []
    missed = []
    missed_points = 0
    bad_points = 0
    correct_count = 0
    for src_index, src in enumerate(reference_src):
        tar = reference_tar[src_index]
        if src not in aligned_src:  # no match here between src lists
            missed_points += 1
            missed.append(src)
            continue
        tar_index = aligned_src.index(src)
        if aligned_tar[tar_index] != tar:
            bad_points += 1
            bad.append(src)
        else:
            correct_count += 1

    # find noise. Penalize by 1 point per noisy item
    noise = []
    noise_points = 0
    for src_index, src in enumerate(aligned_src):
        if src not in reference_src:
            noise_points += 1
            noise.append(src)

    # apply weights to penalty factors
    bad_points = bad_points * penalty_points['bad']
    noise_points = noise_points * penalty_points['noise']
    missed_points = missed_points * penalty_points['missed']
    # find score
    # score = (len(reference_src) - bad_points - noise_points - missed_points) / len(reference_src)
    error_rate = (bad_points + noise_points) / len(reference_src)
    return {'correct_count': "{}/{}".format(correct_count, len(reference_src)), 'error_rate': error_rate,
            'correct_rate': correct_count / len(reference_src), 'bad_points': bad_points,
            'noise_points': noise_points, 'missed_points': missed_points, 'bad': bad, 'noise': noise, 'missed': missed}
