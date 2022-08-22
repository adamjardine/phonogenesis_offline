from __future__ import annotations

from typing import Dict, Any, List

from script import Word, Template, Rule


def get_random_phonemes(interested_words: List[List[Word]]) -> List[Word]:
    from script.phonemes import import_default_randomized_phonemes

    return import_default_randomized_phonemes(interested_words)


def get_full_phonemes() -> List[Word]:
    from script.phonemes import import_default_full_phonemes

    return import_default_full_phonemes()


def translate_templates_data(data_set, template_data: str) -> List[Template]:
    from script import parse_template_line
    template_lines = str(template_data).split("\n")
    templates = []  # type: List[Template]

    for template_line in template_lines:
        templates.append(parse_template_line(template_line, data_set['features']))

    return templates


def translate_phoneme_data(phoneme_data: str) -> List[Word]:
    phoneme_sounds = phoneme_data.split(" ")
    phonemes = []  # type: List[Word]

    for phoneme_sound in phoneme_sounds:
        phonemes.append(Word(phoneme_sound))

    return phonemes


def translate_rule_data(data_set, rule_data: str) -> Rule:
    from script import interpret_rule_content_str

    return interpret_rule_content_str(rule_data, data_set['features'], "Professor Customized", None)


def get_default_data() -> Dict[str, Any]:
    """
    features  # type: List[str]\n
    sounds  # type: List[Sound]\n
    t2fs  # type: Dict[str, List[str]]\n
    f2t  # type: Dict[str, str]\n
    f2ss  # type: Dict[str, List[Sound]]\n
    fs2s  # type: Dict[Particle, Sound]\n
    templates  # type: List[Template]\n
    rule_fam  # type: List[RuleFamily]\n
    rules  # type: List[Rule]\n
    phonemes  # type: List[Word]\n
    gloss_fam # type: List[GlossFamily]\n
    gloss_grp  # type: List[GlossGroup]\n

    :return: dict containing data read from default files
    """
    from script.feature_lib import import_default_features
    from script.rules import import_default_rules
    from script.glossgroup import import_default_gloss
    from script.templates import import_default_templates
    from script.phonemes import import_default_full_phonemes
    _feature_data = import_default_features()

    features = _feature_data[0]
    sounds = _feature_data[1]
    type_to_features = _feature_data[2]
    feature_to_type = _feature_data[3]
    feature_to_sounds = _feature_data[4]
    phonemes = import_default_full_phonemes()

    templates = import_default_templates(features)

    _rule_data = import_default_rules(features)
    rule_families = _rule_data[0]
    rules = {}

    for rule in _rule_data[1]:
        rules[rule.get_name()] = rule

    gloss_data = import_default_gloss()
    gloss_families = gloss_data[0]
    gloss_groups = gloss_data[1]

    return {"features": features, "sounds": sounds, "t2fs": type_to_features, "f2t": feature_to_type,
            "f2ss": feature_to_sounds, "templates": templates, "rule_fam": rule_families, "rules": rules,
            "gloss_fam": gloss_families, "gloss_grp": gloss_groups, "phonemes": phonemes}
