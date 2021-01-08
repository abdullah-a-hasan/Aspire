import argparse
import json
from aspire_aligner.aligner import TranslationAligner, logging
from aspire_aligner.helpers import file_to_list
from aspire_aligner.semantic_libs import tfidf_scikit
from aspire_aligner.helpers import batch_file_to_dict_list


def batch_process(batch_file, output_filename='alignments', input_dir='', output_dir='', output_format='tmx',
                  options_file=None):
    if input_dir is None:
        input_dir = ''
    if output_dir is None:
        output_dir = ''
    try:
        batch_dict = batch_file_to_dict_list(batch_file)
    except Exception as e:
        logging.error('batch_process: could not read or process provided batch file. %r', str(e))
        raise

    opts = 'auto'
    if options_file is not None:
        try:
            with open(options_file) as json_file:
                opts = json.load(json_file)
        except Exception as e:
            logging.error('batch_process: could not load options from json file. %r', str(e))
            raise

    tfidf_semantic_class = tfidf_scikit.TfidfComp
    alg = TranslationAligner()
    alg.batch_align(tfidf_semantic_class, batch_dict=batch_dict, input_dir=input_dir, output_dir=output_dir,
                    file_format=output_format, options=opts)


def single_process(src_file, tar_file, src_mt_file=None, tar_mt_file=None, output_filename='alignments',
                   output_format='tmx', options_file=None):
    src, tar, src_mt, tar_mt = [], [], [], []
    try:
        src = file_to_list(src_file)
        tar = file_to_list(tar_file)
        if src_mt_file:
            src_mt = file_to_list(src_mt_file)
        if tar_mt_file:
            tar_mt = file_to_list(tar_mt_file)
    except Exception as e:
        logging.error('single_process: error reading file(s). %r', str(e))
        raise

    opts = 'auto'
    if options_file is not None:
        try:
            with open(options_file) as json_file:
                opts = json.load(json_file)
        except Exception as e:
            logging.error('single_process: could not load options from json file. %r', str(e))
            raise

    tfidf_semantic_class = tfidf_scikit.TfidfComp
    alg = TranslationAligner()
    alg.align(tfidf_semantic_class, src, tar, src_mt, tar_mt, opts)
    exp_file = ''
    if output_format == 'json':
        exp_file = '{}.json'.format(output_filename)
        alg.export_json_dict(exp_file)
    else:
        json_dict = alg.export_json_dict()
    if output_format == 'xls_verbose':
        exp_file = '{}.xls'.format(output_filename)
        alg.export_excel_verbose(exp_file, json_dict)
    elif output_format == 'xls':
        exp_file = '{}.xls'.format(output_filename)
        alg.export_excel(exp_file, json_dict)
    elif output_format == 'tmx':
        exp_file = '{}.tmx'.format(output_filename)
        alg.export_tmx(exp_file, json_dict)

def run_app():
    parser = argparse.ArgumentParser()
    batch_group = parser.add_argument_group('Batch alignment arguments')
    batch_group.add_argument("-b", "--batch",
                             help="XLS or CSV file listing file names of under columns src, mt, src_mt, and tar_mt, See provided XLS sample.")
    batch_group.add_argument("-od", "--output_dir", help="Output directory.")
    batch_group.add_argument("-id", "--input_dir",
                             help="Root directory, which will be added as a prefix to file names in the XSL or CSV file.")

    single_group = parser.add_argument_group('Single pair alignment arguments')
    single_group.add_argument("-src", help="Source file.")
    single_group.add_argument("-tar", help="Target file.")
    single_group.add_argument("-src_mt", help="MT of source file.")
    single_group.add_argument("-tar_mt", help="MT of target file.")

    parser.add_argument("-fn", "--file_name", default='alignments', help="Output file name without extension.")
    parser.add_argument("-fmt", "--format", choices=['tmx', 'xls', 'xls_verbose', 'json'], default='tmx',
                        help="TMX, XLS, VERBOSE_XLS, or JSON.")
    parser.add_argument("-opt", "--options",
                        help="JSON file containing alignment options. See provided sample_options.json")
    args = parser.parse_args()
    print(args)

    # verify argument combinations
    if args.batch:
        if args.src or args.tar or args.src_mt or args.tar_mt:
            parser.error("cannot combine -b with -src, -tar, -src_mt, or -tar_mt.")
        batch_process(batch_file=args.batch, output_filename=args.file_name, input_dir=args.input_dir,
                      output_dir=args.output_dir, output_format=args.format, options_file=args.options)
    if args.src:
        if args.tar is None or (args.src_mt is None and args.tar_mt is None):
            parser.error("-src requires -tar and -src_mt or -tar_mt.")
        single_process(args.src, args.tar, args.src_mt, args.tar_mt, args.file_name, args.format, args.options)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run_app()
