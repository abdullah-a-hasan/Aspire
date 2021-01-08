import sys
import os
import json
import re
from pathlib import Path

# Globals
current_path = os.path.dirname(os.path.abspath(__file__))  # dir of current file
app_root = os.path.dirname(current_path)  # dir where aspire_app is located
export_path = os.path.join(current_path, 'static', 'download')
srx_file_path = os.path.join(current_path, 'web_dynamic', 'py_srx_segmenter', 'default_rules.srx')
sys.path.append(
    app_root)  # this is important because this file lives in a virtual directory and I need to accesss my code elsewhere

import time
from flask import Flask, send_from_directory
from flask import request, url_for, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from users import *
from newspaper import Article  # pip install newspaper3k
import langdetect as lang_detect
from web_dynamic import mt_helpers
from web_dynamic.py_srx_segmenter import srx_segmenter
from aspire_aligner.aligner import TranslationAligner
from aspire_aligner.semantic_libs import tfidf_scikit, fuzzy_comp
import random
import string

# Flask
app = Flask(__name__, static_folder=None)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username


@app.route('/')
@auth.login_required
def home():
    return redirect('static/align.html')


# protect static files too
@app.route('/static/<path:path>', methods=['GET'])
@auth.login_required
def getStaticPath(path):
    print("serving from static")
    return send_from_directory('static', path)


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/align', methods=['POST'])
@auth.login_required
def align_row_text():
    source_text = request.form['source_text']
    target_text = request.form['target_text']
    # check if source and target are urls
    url_rex = r"(?i)\b(?:(?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\))+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    if re.fullmatch(url_rex, source_text.strip().lower()):
        src_article = Article(source_text.strip())
        src_article.download()
        src_article.parse()
        source_text = src_article.title + "\n" + src_article.text
    if re.fullmatch(url_rex, target_text.strip().lower()):
        tar_article = Article(target_text.strip())
        tar_article.download()
        tar_article.parse()
        target_text = tar_article.title + "\n" + tar_article.text

    # segment source and target

    src_lang_code = lang_detect.detect(source_text)
    tar_lang_code = lang_detect.detect(target_text)

    if src_lang_code == 'zh-cn':
        srx_src_code = 'Generic'
    else:
        srx_src_code = src_lang_code

    if tar_lang_code == 'zh-cn':
        srx_tar_code = 'Generic'
    else:
        srx_tar_code = tar_lang_code

    srx_rules = srx_segmenter.parse(srx_file_path)
    seg_results = srx_segmenter.SrxSegmenter(srx_rules[srx_src_code], source_text)
    source_list = seg_results.extract()[0]
    seg_results = srx_segmenter.SrxSegmenter(srx_rules[srx_tar_code], target_text)
    target_list = seg_results.extract()[0]
    # translate target
    target_mt_list = mt_helpers.google_translate_chunk_by_chunk(target_list, tar_lang_code, src_lang_code)
    # align
    # initiate the alignment class
    algorithm = request.form.get('algorithm', 'fuzzy')
    align_options = {"location_weight": float(request.form.get('input_location_weight', 0.2)),
                     "length_weight": float(request.form.get('input_length_weight', 0.1)),
                     "meta_weight": float(request.form.get('input_length_weight', 0.1)),
                     "semantic_weight": float(request.form.get('input_semantic_weight', 0.6)),
                     "search_range": float(request.form.get('input_paragraph_size', 5)),
                     "minimum_semantic_score": float(request.form.get('input_minimum_semantic_score', 0.5)),
                     "minimum_partial_sem_match": 0.1,
                     "minimum_length_score": float(request.form.get('input_minimum_length_score', 0.6))}

    if algorithm == 'fuzzy':
        semantic_class = fuzzy_comp.FuzzyComp
    else:
        semantic_class = tfidf_scikit.TfidfComp
    alg = TranslationAligner()

    alg.align(semantic_class, source_list, target_list, [], target_mt_list, options=align_options)
    # save json file to a random file name under static files and return it with the results
    temp_file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    temp_json_file_name = temp_file_name + ".json"
    alg.export_json_dict(os.path.join(export_path, temp_json_file_name))
    del alg
    return {"json_file_name": temp_json_file_name}


@app.route('/gen-tmx', methods=['POST'])
@auth.login_required
def gen_tmx():
    json_dict = json.loads(request.form['json_dict'])
    temp_tmx_file_name = json_dict['meta']['source_language'] + '_' + json_dict['meta']['target_language'] + '_'
    temp_tmx_file_name += ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    temp_tmx_file_name += '.tmx'
    TranslationAligner.export_tmx(os.path.join(export_path, temp_tmx_file_name), json_dict)
    del json_dict
    return {"tmx_file_name": temp_tmx_file_name}


@app.route('/gen-xls', methods=['POST'])
@auth.login_required
def gen_xls():
    json_dict = json.loads(request.form['json_dict'])
    temp_xls_file_name = json_dict['meta']['source_language'] + '_' + json_dict['meta']['target_language'] + '_'
    temp_xls_file_name += ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    temp_xls_file_name += '.xls'
    TranslationAligner.export_excel(os.path.join(export_path, temp_xls_file_name), json_dict)
    del json_dict
    return {"xls_file_name": temp_xls_file_name}
