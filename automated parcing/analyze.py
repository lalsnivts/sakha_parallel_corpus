# import configparser
# import logging
import os
import re
import sys

import hfst

# config = configparser.ConfigParser()
# config.read('settings.ini')
transducer_morf = hfst.HfstInputStream("sah.automorf.hfst").read()
parts_of_speech = [
    '<v>',  # Глагол
    '<n>',  # Имя существительное
    '<adj>',  # Имя прилагательное
    '<np>',  # Имя ...
    '<cnjcoo>',  # Союз
    '<post>',  # Послелог
    '<det>',  # Детерминатор
    '<adv>',  # Наречие
    '<postadv>',  # Посленаречие
    '<vaux>',  # Помогительный глагол
    '<ij>',  # Interjection
    '<cnjadv>',  # Подчинительный союз
    '<cnjsub>',  # Подчинительный союз; Sub-ordinating conjunction
    '<num>',  # Число
    '<prn>',  # Местоимение
    '<abbr>',  # Abbreviation
    '<qst>',  # Question word
    '<cop>',  # Связка
    '<mod>'  # modal particle
]
glosses_ignor = ['<nom>', '<sg>', '<tv>', '<iv>']
gloss_mapping = {}


def load_mapping(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.readlines()
        for line in text:
            l = line.replace('\n', '').split(";")
            gloss_mapping.update({l[0]: l[1].split(",")})


def check_params(args):
    if len(args) < 3:
        raise ValueError('Проверьте, что указали все необходимые файлы.')
    if not os.path.exists(args[1]):
        raise FileExistsError('Проверьте, что входной файл существует.')
    if not args[2].endswith('.txt'):
        raise ValueError('Проверьте, что ввели корректное имя выходного '
                         'файла (расширение .txt)')


def parse(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        with open(output_file, 'w', encoding='utf-8') as res:
            cor_sentences = 0
            all_cor_words = 0
            number_of_words = 0
            text = f.readlines()

            for line in text:
                lines = line.split('\t')
                if len(lines) > 1:
                    cor_sentences, all_cor_words, number_of_words = \
                        parse_evaluate(lines, res, cor_sentences, all_cor_words, number_of_words)
                else:
                    parse_simple(lines[0], res)
            if number_of_words > 0:
                cor_percent_all = percentage(all_cor_words, number_of_words)
                res.write('Кол-во верных предложений: ' + str(cor_sentences) + '\n')
                res.write('Общий процент верных слов: ' + str(cor_percent_all))


def parse_evaluate(lines, res, cor_sentences, all_cor_words, number_of_words):
    sah = lines[0]
    descs = lines[1].split(' ')
    sah = sah.replace('- ', '')
    #          rus = line.split('\t')[1]
    res.write(sah + '\n')
    #          res.write(rus + '\n')
    clean = re.sub(r'[^\w\s-]', ' ', sah)
    cor_words = 0
    for i, word in enumerate(clean.split()):
        if '-' in word:
            lemma = word[:word.find('-')].lower()
        else:
            lemma = word.lower()
        word = word.replace('-', '')
        glosses = transducer_morf.lookup(word.lower())
        glosses_cleaned = [gloss[0][gloss[0].index('<'):] for gloss in glosses]
        desc_str = (descs[i] if i < len(descs) else '').replace('(?)', '').replace('\n', '')
        desc = desc_str.split('-')
        if len(desc) > 0 and not desc[0].isupper():
            del desc[0]
        for n in range(len(desc)-1, -1, -1):
            if not desc[n] in gloss_mapping.keys():
                res.write('Ошибка в глоссах: ' + desc[n] + '\n')
                del desc[n]
        res.write(str(i + 1) + '  ' + word + '\t' + desc_str + '\n')
        #                if len(glosses) == 0:
        #                    res.write(str(i + 1) + 'g ' + word + '\n')
        #                else:
        if len(glosses) > 0:
            is_word_correct = False
            for n in range(0, len(glosses)):
                is_correct, excess_glosses = evaluate(lemma, glosses_cleaned[n], desc)
                if is_correct:
                    is_word_correct = True
                res.write(str(i + 1) + 'g ' + glosses[n][0] + '\t' +
                          ('correct' if is_correct else 'wrong') +
                          (', но нашлись лишние глоссы: ' + ','.join(excess_glosses) if len(excess_glosses) > 0 else '')
                          + '\n')
            if is_word_correct:
                cor_words += 1
                all_cor_words += 1
    if cor_words == len(clean.split()):
        cor_sentences += 1
    cor_percent = percentage(cor_words, len(clean.split()))
    number_of_words = number_of_words + len(clean.split())
    res.write('Процент правильных слов: ' + str(cor_percent) + '\n')
    res.write('\n')
    return cor_sentences, all_cor_words, number_of_words


def parse_simple(line, res):
    sah = line
    sah = sah.replace('- ', '')
    #          rus = line.split('\t')[1]
    res.write(sah + '\n')
    #          res.write(rus + '\n')
    clean = re.sub(r'[^\w\s-]', ' ', sah)
    for i, word in enumerate(clean.split()):
        if '-' in word:
            lemma = word[:word.find('-')].lower()
        else:
            lemma = word.lower()
        word = word.replace('-', '')
        glosses = transducer_morf.lookup(word.lower())
        res.write(str(i + 1) + '  ' + word + '\n')
        #                if len(glosses) == 0:
        #                    res.write(str(i + 1) + 'g ' + word + '\n')
        #                else:
        if len(glosses) > 0:
            for n in range(0, len(glosses)):
                res.write(str(i + 1) + 'g ' + glosses[n][0] + '\n')


def percentage(part, whole):
    return round(100 * float(part) / float(whole), 2)


def evaluate(word, glosses, desc):
    excess_glosses = []
    if len(desc) == 0 and glosses.replace('<nom>', '') in parts_of_speech:
        return True, excess_glosses
    if len(desc) == 0 and glosses.replace('<nom>', '') not in parts_of_speech:
        return False, excess_glosses
    pos = 0
    glosses_list = []
    while pos < len(glosses):
        glosses_list.append(glosses[pos:glosses.index('>', pos) + 1])
        pos = glosses.index('>', pos) + 1
    for d in desc:
        if not any((gm in glosses) or gm == "?" for gm in gloss_mapping[d]):
            return False, excess_glosses
    mapped_glosses = [s for gm in [gloss_mapping[d] for d in desc] for s in gm]
    excess_glosses = [g for g in glosses_list
                      if g not in mapped_glosses
                      and g not in glosses_ignor
                      and g not in parts_of_speech]
    return True, excess_glosses


def main():
    check_params(sys.argv)

    # logging.basicConfig(filename="logfile.log", level=logging.ERROR)
    load_mapping("gloss_mapping.txt")
    parse(sys.argv[1], sys.argv[2])
    # 'dubrovskiy_aligned.csv'
    # 'dubrovsky_parsed.txt'


if __name__ == '__main__':
    main()
