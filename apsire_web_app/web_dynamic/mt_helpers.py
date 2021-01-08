import time
import html
import json
import hashlib
import os.path
# from pathlib import Path
from google.cloud import translate_v2  # pip install google-cloud / pip install google-cloud-translate
import requests  # general api library. Good enough for modernmt

# Globals

# current_path = str(Path(__file__).parent)
current_path = os.path.dirname(os.path.abspath(__file__))

google_conf_path = os.path.join(current_path, 'google_trans_api_auth', 'creds.json')
mt_cache_dir = os.path.join(current_path, 'mt_cache')


def load_trans_from_cache(source_lang, target_lang, source_strings):
    # hash the source_strings
    source_to_json = json.dumps(source_strings)
    source_to_md5 = hashlib.md5(source_to_json.encode()).hexdigest()
    # construct cache file path
    chache_file_path = os.path.join(mt_cache_dir, "{}_{}_{}.trs".format(source_lang, target_lang, source_to_md5))

    # check cache path existence
    if os.path.exists(chache_file_path):
        with open(chache_file_path, "r", encoding="utf8") as text_file:
            cache_content = text_file.read()
            text_file.close()
        # decode cache
        target_strings = json.loads(cache_content)
        return target_strings
    else:
        return False


def save_trans_to_cache(source_lang, target_lang, source_strings, target_strings):
    # hash the source_strings
    source_to_json = json.dumps(source_strings)
    source_to_md5 = hashlib.md5(source_to_json.encode()).hexdigest()
    # jsonify the target_strings
    target_to_json = json.dumps(target_strings)
    # construct cache file path
    chache_file_path = os.path.join(mt_cache_dir, "{}_{}_{}.trs".format(source_lang, target_lang, source_to_md5))
    # save cache
    with open(chache_file_path, "w", encoding="utf8") as text_file:
        text_file.write(target_to_json)
        text_file.close()
    return True


def chunk_str_list(fat_list, max_chars_per_list):
    """
    Splits a string list into multiple lists based on max_chars_per_list for processing over size-limited MT APIs
    """
    text_len = 0
    parent_list = []
    starting_point = 0
    for (index, text) in enumerate(fat_list):
        text_len += len(text)
        if text_len > max_chars_per_list or index == len(fat_list) - 1:  # and index != 0:
            parent_list.append(fat_list[starting_point:index + 1])
            starting_point = index + 1
            text_len = 0
    return parent_list


def google_translate(source_strings=[], source_lang='auto', target_lang='en'):
    key_file = google_conf_path
    t_client = translate_v2.Client.from_service_account_json(key_file)
    results = t_client.translate(source_strings, source_language=source_lang, target_language=target_lang, model="nmt")
    translations_strings = []
    for item in results:
        translations_strings.append(item["translatedText"])
    return translations_strings


def google_translate_chunk_by_chunk(source_strings=[], source_lang='auto', target_lang='en'):
    trans_from_cache = load_trans_from_cache(source_lang, target_lang, source_strings)
    if trans_from_cache:
        print('Translation already exists and was loaded from cache')
        return trans_from_cache
    print('Uncached. Will get translations from provider.')
    key_file = google_conf_path
    t_client = translate_v2.Client.from_service_account_json(key_file)

    # divide long string list into smaller ones to avoid hitting google's limit
    chunked_source_strings = chunk_str_list(source_strings, 2000)
    translations_strings = []
    for sub_list in chunked_source_strings:
        results = t_client.translate(sub_list, source_language=source_lang, target_language=target_lang, model="nmt")
        wait_time = 0.5
        print("Google translate trip. Will wait {} second(s)...".format(wait_time))
        time.sleep(wait_time)
        for item in results:
            translations_strings.append(html.unescape(item["translatedText"]))
    with open("google_translated_file.txt", "w", encoding='utf-8') as outfile:
        outfile.write("\n".join(translations_strings))
    # save translations to cache
    save_trans_to_cache(source_lang, target_lang, source_strings, translations_strings)
    return translations_strings
