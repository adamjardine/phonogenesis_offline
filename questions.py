import random
from script import *
from script.morphology import ParadigmGenerator

def supported_rule_families_name(default_rules):
    morph_rule_dic = {}
    edge_rules = [r for r in default_rules if r._Cs_edge == [False] and r._Ds_edge == [False]]
    for rule in edge_rules:
        if rule.get_family() not in morph_rule_dic:
            morph_rule_dic[rule.get_family()] = 1
        else:
            morph_rule_dic[rule.get_family()] += 1
    return [fam.get_name() for fam in morph_rule_dic.keys()]



def get_morphology_question(data,DEFAULT_DATA):
    """
    Modified from function in ../app/routes.py
    data should be a dictionary of settings including 'shuffle':bool, 'isIPAg':bool,'rule_family':str, where either "Random" or one of the families in the 'family' column in data/defaultrules.csv
    DEFAULT_DATA is the set of data to work with (drawn from script.get_default_data())
    """

    # data = request.json

    if 'shuffle' not in data or 'isIPAg' not in data or 'rule_family' not in data:
        raise Exception("Input settings aren't correct")
    try:
        shuffle = bool(data['shuffle'])
        isIPAg = bool(data['isIPAg'])
    except ValueError:
        raise Exception("Input settings aren't correct")
        return

    q_data = None
    rule_type = None
    reset_limit = 10
    try_count = 0
    rule_family = data['rule_family']
    rules = list(DEFAULT_DATA['rules'].values())

    # TODO: Temporarily ignoring all rules that involves edge environments
    rules = [r for r in rules if r._Cs_edge == [False] and r._Ds_edge == [False]]

    if rule_family == "Random":
        rule_family = random.choice(supported_rule_families_name(rules))
        print(rule_family)
        # rule = random.choice(rules)
    rule = random.choice([r for r in rules if r.get_family().get_name() == rule_family])

    while try_count < reset_limit:
        q_data = None
        while True:
            try:
                phonemes = get_random_phonemes([rule.get_a_matcher(None, None, DEFAULT_DATA['f2ss'])])
                rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
                p_gen = ParadigmGenerator(rule, phonemes, DEFAULT_DATA['templates'], DEFAULT_DATA['f2t'],
                                          DEFAULT_DATA['f2ss'])
                q_data = p_gen.get_paradigm_question(shuffle, isIPAg, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'],
                                                     affix_type=random.choice(["PREFIX", "SUFFIX"]))
            except IndexError as e:
                try_count += 1
                print("Attempt "+str(try_count)+": error at index "+str(e))
                pass
            if q_data is None:
                try_count += 1
                pass
            else:
                break
        if q_data is not None:
            break

    if q_data:
        morphology_question = {'qType': "Morphology", 'templates': q_data['templates'],
                               'poi': q_data['poi'], 'rule_type': str(rule_type),
                               'phonemes': ' '.join(q_data['phonemes']),
                               'rule_name': rule.get_name(), 'gloss': q_data['Gloss'], 'UR': q_data['ur_words'],
                               'core_data': q_data['core_data'], 'canUR': True, 'canPhoneme': True,
                               'rule_content': rule.get_content_str(), 'rule_family': rule.get_family().get_name(),
                               'header_row': q_data['header_row'], 'trans_patterns': q_data['trans_patterns']}

        # return jsonify(success=True, question=morphology_question)
        return morphology_question
    else:
        raise Exception("Sorry! Failed to get a question. Please try again.")
