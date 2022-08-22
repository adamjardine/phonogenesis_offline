from __future__ import annotations

import os
import random
import sys
from typing import List, Dict, Tuple

from script.feature_lib import import_default_features
from script.glossgroup import import_default_gloss
from script.morphology import ParadigmGenerator
from script.phonemes import import_default_full_phonemes
from script.rules import Rule, RuleFamily, import_default_rules
from script.sound import Sound
from script.templates import Template, import_default_templates
import script.word as word


def _print_result(rst: dict):
    if rst is None:
        print("No result.")
        return
    print("UR:", rst["UR"], ",")
    print("SR:", rst["SR"], ",")
    print("gloss: ", rst["Gloss"], ",")
    print("ruleTxt: \"", rst["rule"].split(" ===== ")[0] + "\"")


def random_select(families: List[RuleFamily], rules_: List[Rule], family_num: int, rule_num: int) -> List[Rule]:
    if family_num > rule_num:
        raise AttributeError("family num larger than rule num")

    if len(families) < family_num:
        raise AttributeError("num greater than family size")

    if len(rules_) < rule_num:
        raise AttributeError("num greater than rule size")

    chosen_family = random.choices(families, k=family_num)  # type: List[RuleFamily]
    rules_pool = [family_.get_rules() for family_ in chosen_family]
    random_result = []

    while rule_num > 0:
        for pool in rules_pool:
            if rule_num <= 0:
                break

            if len(pool) == 0:
                continue

            chosen = random.choice(pool)  # type: Rule
            pool.remove(chosen)
            random_result.append(chosen)
            rule_num -= 1

    return random_result


if __name__ == '__main__':
    tup = import_default_features()

    features = tup[0]  # type: List[str]
    sounds = tup[1]  # type: List[Sound]
    type_to_features = tup[2]  # type: Dict[str, List[str]]
    feature_to_type = tup[3]  # type: Dict[str, str]
    feature_to_sounds = tup[4]  # type: Dict[str, List[Sound]]

    templates = import_default_templates(features)  # type: List[Template]
    #
    # print("full templates: ")
    # ti = 1
    # for template in templates:
    #     print(ti, template)
    #     ti += 1

    rule_data = import_default_rules(features)  # type: Tuple[List[RuleFamily], List[Rule]]
    rule_families = rule_data[0]  # type: List[RuleFamily]
    rules = rule_data[1]  # type: List[Rule]

    # print("\nfull rule families:")
    # fi = 1
    # for family in rule_families:
    #     print(fi, family)
    #     fi += 1
    #
    # print("\nfull rules: ")
    # ri = 1
    # for rule in rules:
    #     print(ri, rule)
    #     ri += 1

    gloss_data = import_default_gloss()
    gloss_families = gloss_data[0]
    gloss_groups = gloss_data[1]
    # #
    # # print("\nfull gloss families: ", [str(f) for f in gloss_families])
    # # print("\nfull gloss groups: ", [str(g) for g in gloss_groups])
    # #
    # # print("\n==================================================\n")
    #
    # print([str(s) for s in gloss_families[1].get_members()])
    #
    # print("Rule Size: ", len(rules))
    #
    # manual_rule_select = 1
    #
    use_rule = rules[66]

    amount = 40

    # phonemes = import_default_randomized_phonemes([use_rule.get_a_matcher(None, None, feature_to_sounds),
    #                                                use_rule.get_c_matchers(None, feature_to_sounds),
    #                                                use_rule.get_d_matchers(None, feature_to_sounds)])
    #

    phonemes = import_default_full_phonemes()
    psr = "phoneme: \""
    for p in phonemes:
        psr += str(p) + " "
    print(psr + "\",")
    print(str(use_rule))

    print(str(use_rule.apply(word.Word("adadadad"), phonemes, feature_to_type, feature_to_sounds)[0]))

    # p_gen = ParadigmGenerator(use_rule, phonemes, templates, feature_to_type, feature_to_sounds)
    # pdim = p_gen._get_valid_question(False, "PREFIX")
    # print(str(pdim))
    # print(pdim.valid_row_indexes())
    # word1 = word.Word("fuku")
    # print(word1.is_appropriate())
    #
    # # rule1 = rules[96]
    # # rule2 = rules[97]
    # # df = DoubleFeed(rule1, rule2, InteractionOrder.Feeding, False, DoubleWordDifficulty.Easy, phonemes, templates, feature_to_type,
    # #                 feature_to_sounds)
    # # df_data = df.generate(30)
    # # print("RULE1", str(rule1))
    # # print("RULE2", str(rule2))
    # # print("BLOCKA", [str(w) for w in df_data[0]])
    # # print("BLOCKB", [str(w) for w in df_data[1]])
    # # print("BLOCKC", [str(w) for w in df_data[2]])
    # # print("BLOCKD", [str(w) for w in df_data[3]])
    #
    # # while True:
    # #     # word = input("\nWord to check: ")
    # #     word = "gɛgə"
    # #     print(rules[manual_rule_select])
    # #     print(rules[manual_rule_select].classify(Word(word), phonemes, feature_to_type, feature_to_sounds))
    # #     print(str(rules[manual_rule_select].apply(Word(word), phonemes, feature_to_type, feature_to_sounds)[0]))
    # #     break
    #
    # print("ruleType: \"" + str(use_rule.get_rule_type(phonemes, feature_to_type, feature_to_sounds)) + "\",")
    # use_templates = templates
    #
    # print("\nUSING RULE: ", use_rule)
    # print("\nGENERATION AMOUNT:", amount, '\n')
    #
    # interest = use_rule.get_interest_phones(phonemes, feature_to_type, feature_to_sounds)[1]
    # isr = "poi: \""
    # for i in interest:
    #     isr += str(i) + " "
    # print(isr + "\",")
    #
    # print(use_rule.classify(Word("səʃpit"), phonemes, feature_to_type, feature_to_sounds))
    #
    # print(str(use_rule.apply(Word("səʃpit"), phonemes, feature_to_type,feature_to_sounds)[0]))
    # print(use_rule.get_a_matcher(phonemes, None, feature_to_sounds) == [''])
    # gen = Generator(phonemes, templates, use_rule, 5, feature_to_type, feature_to_sounds)
    #
    # result = gen.generate(GenMode.IPAg, [5, 0, 0, 0, 0], True, False, gloss_groups)
    #
    # _print_result(result)
