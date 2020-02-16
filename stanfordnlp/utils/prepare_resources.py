import json
import argparse
import torch
import os
from pathlib import Path
import hashlib
import shutil
import zipfile


# list of language shorthands
conll_shorthands = ['af_afribooms', 'ar_padt', 'bg_btb', 'bxr_bdt', 'ca_ancora', 'cs_cac', 'cs_fictree', 'cs_pdt', 'cu_proiel', 'da_ddt', 'de_gsd', 'el_gdt', 'en_ewt', 'en_gum', 'en_lines', 'es_ancora', 'et_edt', 'eu_bdt', 'fa_seraji', 'fi_ftb', 'fi_tdt', 'fr_gsd', 'fro_srcmf', 'fr_sequoia', 'fr_spoken', 'ga_idt', 'gl_ctg', 'gl_treegal', 'got_proiel', 'grc_perseus', 'grc_proiel', 'he_htb', 'hi_hdtb', 'hr_set', 'hsb_ufal', 'hu_szeged', 'hy_armtdp', 'id_gsd', 'it_isdt', 'it_postwita', 'ja_gsd', 'kk_ktb', 'kmr_mg', 'ko_gsd', 'ko_kaist', 'la_ittb', 'la_perseus', 'la_proiel', 'lv_lvtb', 'nl_alpino', 'nl_lassysmall', 'no_bokmaal', 'nn_nynorsklia', 'nn_nynorsk', 'pl_lfg', 'pl_sz', 'pt_bosque', 'ro_rrt', 'ru_syntagrus', 'ru_taiga', 'sk_snk', 'sl_ssj', 'sl_sst', 'sme_giella', 'sr_set', 'sv_lines', 'sv_talbanken', 'tr_imst', 'ug_udt', 'uk_iu', 'ur_udtb', 'vi_vtb', 'zh_gsd']


# all languages with mwt
mwt_languages = ['ar_padt', 'ca_ancora', 'cs_cac', 'cs_fictree', 'cs_pdt', 'de_gsd', 'el_gdt', 'es_ancora', 'fa_seraji', 'fi_ftb', 'fr_gsd', 'fr_sequoia', 'gl_ctg', 'gl_treegal', 'he_htb', 'hy_armtdp', 'it_isdt', 'it_postwita', 'kk_ktb', 'pl_sz', 'pt_bosque', 'tr_imst']


# default treebank for languages
default_treebanks = {'af': 'af_afribooms', 'grc': 'grc_proiel', 'ar': 'ar_padt', 'hy': 'hy_armtdp', 'eu': 'eu_bdt', 'bg': 'bg_btb', 'bxr': 'bxr_bdt', 'ca': 'ca_ancora', 'zh': 'zh_gsd', 'hr': 'hr_set', 'cs': 'cs_pdt', 'da': 'da_ddt', 'nl': 'nl_alpino', 'en': 'en_ewt', 'et': 'et_edt', 'fi': 'fi_tdt', 'fr': 'fr_gsd', 'gl': 'gl_ctg', 'de': 'de_gsd', 'got': 'got_proiel', 'el': 'el_gdt', 'he': 'he_htb', 'hi': 'hi_hdtb', 'hu': 'hu_szeged', 'id': 'id_gsd', 'ga': 'ga_idt', 'it': 'it_isdt', 'ja': 'ja_gsd', 'kk': 'kk_ktb', 'ko': 'ko_kaist', 'kmr': 'kmr_mg', 'la': 'la_ittb', 'lv': 'lv_lvtb', 'sme': 'sme_giella', 'no_bokmaal': 'no_bokmaal', 'nn_nynorsk': 'nn_nynorsk', 'cu': 'cu_proiel', 'fro': 'fro_srcmf', 'fa': 'fa_seraji', 'pl': 'pl_lfg', 'pt': 'pt_bosque', 'ro': 'ro_rrt', 'ru': 'ru_syntagrus', 'sr': 'sr_set', 'sk': 'sk_snk', 'sl': 'sl_ssj', 'es': 'es_ancora', 'sv': 'sv_talbanken', 'tr': 'tr_imst', 'uk': 'uk_iu', 'hsb': 'hsb_ufal', 'ur': 'ur_udtb', 'ug': 'ug_udt', 'vi': 'vi_vtb'}


# default ner for languages
default_ners = {'ar': 'ontonotes', 'de': 'conll03', 'en': 'conll03', 'es': 'conll02', 'fr': 'wikiner', 'nl': 'conll02', 'ru': 'wikiner', 'zh': 'ontonotes'}


# default charlms for languages
default_charlms = {'ar': [['charlm', 'ccwiki_backward'], ['charlm', 'ccwiki_forward']], 'de': [['charlm', 'newswiki_backward'], ['charlm', 'newswiki_forward']], 'en': [['charlm', '1billion_backward'], ['charlm', '1billion_forward']], 'es': [['charlm', 'newswiki_backward'], ['charlm', 'newswiki_forward']], 'fr': [['charlm', 'newswiki_backward'], ['charlm', 'newswiki_forward']], 'nl': [['charlm', 'ccwiki_backward'], ['charlm', 'ccwiki_forward']], 'ru': [['charlm', 'newswiki_backward'], ['charlm', 'newswiki_forward']], 'zh': [['charlm', 'gigaword_backward'], ['charlm', 'gigaword_forward']]}


# map processor name to file ending
processor_to_ending = {'tokenize': 'tokenizer', 'mwt': 'mwt_expander', 'pos': 'tagger', 'lemma': 'lemmatizer', 'depparse': 'parser', 'ner': 'nertagger', 'pretrain': 'pretrain'}
ending_to_processor = {j: i for i, j in processor_to_ending.items()}


def ensure_dir(dir):
    Path(dir).mkdir(parents=True, exist_ok=True)


def get_md5(path):
    data = open(path, 'rb').read()
    return hashlib.md5(data).hexdigest()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default='/u/apache/htdocs/static/software/stanza/stanfordnlp', help='Input dir for various models.')
    parser.add_argument('--output_dir', type=str, default='/u/apache/htdocs/static/software/stanza/output')
    parser.add_argument('--ner_dir', type=str, default='/u/scr/zyh/develop/stanfordnlp-train/saved_models')
    args = parser.parse_args()
    return args


def handle_pretrain(input_path, output_path):
    model = torch.load(input_path, map_location='cpu')
    model['vocab'] = model['vocab'].state_dict()
    torch.save(model, output_path)


def process_dirs(args):
    dirs = sorted(os.listdir(args.input_dir))
    resources = {}
    for dir in dirs:
        print(dir)
        lang, treebank, _ = dir.split('_')
        models = sorted(os.listdir(os.path.join(args.input_dir, dir)))
        for model in models:
            if not model.endswith('.pt'): continue
            # get processor
            _, _, processor = model.replace('.pt', '').replace('.', '_').split('_', 2)
            processor = ending_to_processor[processor]
            # copy file
            input_path = os.path.join(args.input_dir, dir, model)
            output_path = os.path.join(args.output_dir, lang, processor, treebank + '.pt')
            ensure_dir(Path(output_path).parent)
            if processor == 'pretrain':
                handle_pretrain(input_path, output_path)
            else:
                shutil.copy(input_path, output_path)
            # maintain md5
            md5 = get_md5(output_path)
            # maintain dependencies
            if processor == 'pos' or processor == 'depparse':
                dependencies = [['pretrain', treebank]]
            else:
                dependencies = None
            # maintain resources
            if lang not in resources: resources[lang] = {}
            if processor not in resources[lang]: resources[lang][processor] = {}
            if dependencies:
                resources[lang][processor][treebank] = {'md5': md5, 'dependencies': dependencies}
            else:
                resources[lang][processor][treebank] = {'md5': md5}
    json.dump(resources, open(os.path.join(args.output_dir, 'resources.json'), 'w'), indent=2)


def copy_file(src, dst):
    ensure_dir(Path(dst).parent)
    shutil.copy(src, dst)


def process_ners(args):
    resources = json.load(open(os.path.join(args.output_dir, 'resources.json')))
    ner_models = sorted(os.listdir(os.path.join(args.ner_dir, 'ner')))
    charlm_models = sorted(os.listdir(os.path.join(args.ner_dir, 'charlm')))
    default_charlm = {}
    for model in charlm_models:
        if not model.endswith('charlm.pt'): continue
        print(model)
        splitmodel = model.replace('.pt', '').split('_')
        lang, treebank, processor = splitmodel[0], '_'.join(splitmodel[1:-1]), splitmodel[-1]
        # copy file
        copy_file(os.path.join(args.ner_dir, processor, model), os.path.join(args.output_dir, lang, processor, treebank + '.pt'))
        # maintain md5
        md5 = get_md5(os.path.join(args.output_dir, lang, processor, treebank + '.pt'))
        # maintain resources
        if lang not in resources: resources[lang] = {}
        if processor not in resources[lang]: resources[lang][processor] = {}
        resources[lang][processor][treebank] = {'md5': md5}
        # maintain default charlm
        if lang not in default_charlm: default_charlm[lang] = []
        default_charlm[lang].append([processor, treebank])
    
    
    for model in ner_models:
        if not model.endswith('.pt'): continue 
        print(model)
        splitmodel = model.replace('.pt', '').split('_')
        lang, treebank, processor = splitmodel[0], '_'.join(splitmodel[1:-1]), splitmodel[-1]
        processor = ending_to_processor[processor]
        # copy file
        copy_file(os.path.join(args.ner_dir, processor, model), os.path.join(args.output_dir, lang, processor, treebank + '.pt'))
        # maintain md5
        md5 = get_md5(os.path.join(args.output_dir, lang, processor, treebank + '.pt'))
        # maintain resources
        if lang not in resources: resources[lang] = {}
        if processor not in resources[lang]: resources[lang][processor] = {}
        resources[lang][processor][treebank] = {'md5': md5, 'dependencies': default_charlm[lang]}
    json.dump(resources, open(os.path.join(args.output_dir, 'resources.json'), 'w'), indent=2)
    return default_charlm


def process_defaults(args, default_charlm):
    resources = json.load(open(os.path.join(args.output_dir, 'resources.json')))
    for lang in resources:
        if lang not in default_treebanks: 
            print(lang + ' not in default treebanks!!!')
            continue
        print(lang)
        shorthand = default_treebanks[lang]
        _, treebank = shorthand.split('_')
        ner = default_ners.get(lang, None)
        
        os.chdir(os.path.join(args.output_dir, lang))
        zipf = zipfile.ZipFile('default.zip', 'w', zipfile.ZIP_DEFLATED)
        default_processors = {}
        default_dependencies = {'pos': [['pretrain', treebank]], 'depparse': [['pretrain', treebank]]}
        for processor in ['tokenize', 'mwt', 'lemma', 'pos', 'depparse', 'pretrain']:
            if os.path.exists(os.path.join(args.output_dir, lang, processor, treebank + '.pt')):
                if processor != 'pretrain': default_processors[processor] = treebank
                zipf.write(processor)
                zipf.write(os.path.join(processor, treebank + '.pt'))
        if ner:
            processor = 'ner'
            default_processors[processor] = ner
            zipf.write(processor)
            zipf.write(os.path.join(processor, ner + '.pt'))
            processor = 'charlm'
            zipf.write(processor)
            for dep in default_charlm[lang]:
                _, treebank = dep
                zipf.write(os.path.join(processor, treebank + '.pt'))
            default_dependencies['ner'] = default_charlm[lang]
        zipf.close()
        default_md5 = get_md5(os.path.join(args.output_dir, lang, 'default.zip'))
        resources[lang]['default_processors'] = default_processors
        resources[lang]['default_dependencies'] = default_dependencies
        resources[lang]['default_md5'] = default_md5

    json.dump(resources, open(os.path.join(args.output_dir, 'resources.json'), 'w'), indent=2)


def main():
    args = parse_args()
    process_dirs(args)
    process_ners(args)
    process_defaults(args)


if __name__ == '__main__':
    main()