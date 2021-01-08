# from docx import Document #conda install -c conda-forge python-docx
# from collections import namedtuple
import re
import os
from pandas import *
import xml.etree.ElementTree as ET
from collections import namedtuple


# import unicodedata

def log_msg(msg, log_file='app_activity.log'):
    file_object = open(log_file, 'a')
    file_object.write(msg + "\r\n")
    file_object.close()


def get_xml_namespace(element):
    m = re.match('\{.*\}', element.tag)
    return m.group(0) if m else ''


def strip_html_tags(text):
    return re.sub('<[^<]+?>', ' ', text)


def file_to_list(file_name):
    with open(file_name, encoding="utf8") as f:
        lines = [line.strip() for line in f.readlines()]
        f.close()
    return lines


def list_to_file(strings, file_name):
    with open(file_name, "w", encoding='utf-8') as outfile:
        outfile.write("\n".join(strings))
        outfile.close()


def file_to_text(file_name):
    with open(file_name, encoding="utf8") as f:
        text = f.read()
        f.close()
    return text


def file_to_list_clean_tags(file_name):
    with open(file_name, encoding="utf8") as f:
        lines = [strip_memsource_tags(line).strip() for line in f.readlines()]
        f.close()
    return lines


def strip_memsource_tags(text):
    result = re.sub('({|<)[^{]+?(>|})', ' ', text)
    result = re.sub('\s+', ' ', result)
    return result.strip()


def batch_align(file_matrix):
    pass


def batch_file_to_dict_list(file_name):
    # converts csv, xls, or xlsx file to dict
    ext = os.path.splitext(file_name)[1]
    if ext == '.xls' or ext == '.xlsx':
        xls = ExcelFile(file_name)
        df = xls.parse(xls.sheet_names[0], keep_default_na=False)
    elif ext == '.csv':
        df = pandas.read_csv(file_name, keep_default_na=False)
    else:
        raise Exception('file extension must be csv, xls, or xlsx')
    records = df.to_dict(orient='records')
    return records


def verify_batch_dict_list(batch_dict, root=""):
    # verifies the structure of the batch dict and whether the provided file names exist. If no root is given, file names will be assumed to be absolute.
    row_num = 1
    verdict = True
    feedback = "batch_dict must be a list of dictionaries with 'src', 'tar' and one of 'src_mt' or 'tar_mt' keys. Values of these keys are file names.\n"
    for row in batch_dict:
        src = row.get('src', '')
        tar = row.get('tar', '')
        src_mt = row.get('src_mt', '')
        tar_mt = row.get('tar_mt', '')
        if not src or not tar:
            feedback += "row {}: src or tar missing".format(row_num)
            verdict = False
        if not src_mt and not tar_mt:
            feedback += "row {}: src_mt and tar_mt missing\n".format(row_num)
            verdict = False
        if not os.path.exists(os.path.join(root, src)):
            feedback += "row {}: src file \"{}\" does not exist\n".format(row_num, src)
            verdict = False
        if not os.path.exists(os.path.join(root, tar)):
            feedback += "row {}: tar file \"{}\" does not exist\n".format(row_num, tar)
            verdict = False
        if src_mt and not os.path.exists(os.path.join(root, src_mt)):
            feedback += "row {}: src_mt file \"{}\" does not exist\n".format(row_num, src_mt)
            verdict = False
        if tar_mt and not os.path.exists(os.path.join(root, tar_mt)):
            feedback += "row {}: tar_mt file \"{}\" does not exist\n".format(row_num, tar_mt)
            verdict = False
        row_num += 1
    return {'result': verdict, 'feedback': feedback}


def extract_xlf_segments(file_name, flavor="xlf", include_target=True):
    tree = ET.parse(file_name)
    root = tree.getroot()
    ns = get_xml_namespace(root)
    languageStrings = namedtuple('translationStrings',
                                 'source_strings, target_strings, source_language, target_language')
    source = []
    target = []

    # source_xpath = f"{ns}file/{ns}body/{ns}trans-unit/{ns}seg-source/{ns}mrk"
    # target_xpath = f"{ns}file/{ns}body/{ns}trans-unit/{ns}target/{ns}mrk"

    # trans_unit_path =f"{ns}file/{ns}body/{ns}group/{ns}trans-unit"
    trans_unit_path = f".//{ns}trans-unit"

    # todo: use named tuples
    flavored_paths = {}
    flavored_paths["xlf"] = {"source": f"{ns}seg-source/{ns}mrk", "target": f"{ns}target/{ns}mrk"}
    flavored_paths["sdl"] = {"source": f"{ns}seg-source/{ns}g/{ns}mrk", "target": f"{ns}target/{ns}g/{ns}mrk"}
    flavored_paths["sdl"] = {"source": f"{ns}seg-source/*/{ns}mrk", "target": f"{ns}target/*/{ns}mrk"}
    flavored_paths["memsource"] = {"source": f"{ns}source", "target": f"{ns}target"}
    flavored_paths["wordfast"] = flavored_paths["memsource"]
    flavored_paths["memoq"] = flavored_paths["memsource"]

    for unit in root.findall(trans_unit_path):
        for source_segment in unit.findall(flavored_paths[flavor]['source']):
            # clean_source = unicodedata.normalize('NFKD', ''.join(source_segment.itertext()))
            clean_source = ''.join(source_segment.itertext())
            if flavor == 'memsource':
                clean_source = strip_memsource_tags(clean_source)
            clean_source = strip_html_tags(clean_source)
            source.append(clean_source)
        if include_target:
            for target_segment in unit.findall(flavored_paths[flavor]['target']):
                # clean_target = unicodedata.normalize('NFKD', ''.join(target_segment.itertext()))
                clean_target = ''.join(target_segment.itertext())
                if flavor == 'memsource':
                    clean_target = strip_memsource_tags(clean_target)
                clean_target = strip_html_tags(clean_target)
                target.append(clean_target)

    src_lang = root.find(f".//{ns}file").get('source-language')
    target_lang = root.find(f".//{ns}file").get('target-language')

    return languageStrings(source, target, src_lang, target_lang)
