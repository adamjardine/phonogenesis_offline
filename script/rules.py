from __future__ import annotations

import csv
from enum import Enum
from typing import List, Optional, Dict, Tuple, Set

from script import Word, Particle, Sound, Template
from serializable import Serializable

EDGE_SYMBOL = '#'


class ExampleType(Enum):
    CADT = 0,
    CADNT = 1,
    CAND = 2,
    NCAD = 3,
    IRR = 4

    def __str__(self) -> str:
        return self.name


class RuleType(Enum):
    Neutralizing = 0,
    Alternating = 1,
    Mixed = 2

    def __str__(self) -> str:
        return self.name


def _get_c_instance_matcher(c_instance: Optional[List[Particle], None], phonemes: Optional[List[Sound], None],
                            size_limit: Optional[int, None], feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[
    List[Word], int]:
    if c_instance is None:
        return [], -1
    matcher = Template(c_instance).generate_word_list(phonemes, size_limit, feature_to_sounds)

    return matcher, _get_max_len(matcher)


def _get_max_len(lst: list) -> int:
    max_len = -1
    for m in lst:
        if len(m) > max_len:
            max_len = len(m)
    return max_len


def _get_d_instance_matcher(d_instance: Optional[List[Particle], None], phonemes: Optional[List[Sound], None],
                            size_limit: Optional[int, None], feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[
    List[Word], int]:
    if d_instance is None:
        return [], -1
    matcher = Template(d_instance).generate_word_list(phonemes, size_limit, feature_to_sounds)
    return matcher, _get_max_len(matcher)


class Rule(Serializable):
    """
    A>B/C_D
    """
    _As: List[List[Particle]]
    _B: Optional[Tuple[Optional[None, Particle], List[str], int], None]
    _Cs: List[Optional[List[Particle], None]]
    _Ds: List[Optional[List[Particle], None]]

    _CADT_indexes: Dict[Word, List[Tuple[int, int]]]
    _Cs_edge: List[bool]
    _Ds_edge: List[bool]
    _name: str
    _family: Optional[RuleFamily, None]

    def __init__(self, name: str, family: Optional[RuleFamily, None], a: List[List[Particle]],
                 b: Optional[Tuple[Optional[None, Particle], List[str], int], None],
                 c: List[Optional[List[Particle], None]], c_edge: List[bool], d: List[Optional[List[Particle], None]],
                 d_edge: List[bool]) -> None:
        self._name = name
        self._family = family
        self._As = a
        self._A_matchers = {}
        self._B = b

        if len(c) != len(d):
            raise AttributeError("C and D list can not have different length %s _ %s" % (c, d))

        self._Cs = c
        self._Ds = d
        self._Cs_edge = c_edge
        self._Ds_edge = d_edge

        self._CADT_indexes = {}

    def serialize(self, **kwargs):
        return {
            "name": self._name,
            "family": self._family,
            "content": self.get_content_str()
        }

    def apply(self, word: Word, phonemes: Optional[None, List[Word]], feature_to_type: Dict[str, str],
              feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[Word, int]:
        if word not in self._CADT_indexes.keys():
            if ExampleType.CADT not in self.classify(word, phonemes, feature_to_type, feature_to_sounds):
                return word, 0

        indexes = self._CADT_indexes[word]
        new_word = word
        prev_len = len(new_word)
        len_diff = 0
        old_word = word
        chg_count = 0
        for index in indexes:
            new_word = self._do_replace(new_word, index[0] + len_diff, index[1] + len_diff, feature_to_type,
                                        feature_to_sounds)
            if new_word != old_word:
                old_word = new_word
                chg_count += 1
            new_len = len(new_word)
            len_diff += new_len - prev_len
            prev_len = new_len

        return new_word, chg_count

    def classify(self, word: Word, phonemes: Optional[None, List[Word]], feature_to_type: Dict[str, str],
                 feature_to_sounds: Dict[str, List[Sound]]) -> List[ExampleType]:
        a_data = self.locations_a(word, phonemes, feature_to_sounds)
        a_locations = list(a_data.keys())  # type: List[int]
        is_insertion = self.get_a_matcher(phonemes, None, feature_to_sounds) == ['']
        org_word = word

        if len(a_locations) == 0 or a_locations == []:
            return [ExampleType.IRR for _ in range(0, len(self._Cs))]
        else:
            word_types = [None for _ in range(len(self._Cs))]  # type: List[Optional[None, ExampleType]]

            for i in range(0, len(self._Cs)):
                c_instance = self._Cs[i]
                d_instance = self._Ds[i]
                c_edge = self._Cs_edge[i]
                d_edge = self._Ds_edge[i]

                for a_loc in a_locations:
                    a_size = len(a_data[a_loc])

                    if is_insertion:
                        word = self._do_replace(org_word, a_loc, a_loc, feature_to_type, feature_to_sounds)

                    if c_edge and c_instance is None:
                        is_c = a_loc == 0
                    elif not c_edge and c_instance is None:
                        is_c = True
                    else:
                        is_c = \
                            Template(c_instance[::-1]).is_d_match(word.reverse(), len(word) - 1 - a_loc,
                                                                  c_edge, feature_to_sounds, phonemes)[0]

                    if d_edge and d_instance is None:
                        is_d = a_loc + a_size == len(word)
                    elif not d_edge and d_instance is None:
                        is_d = True
                    else:
                        is_d = Template(d_instance).is_d_match(word, a_loc, d_edge, feature_to_sounds, phonemes)[0]

                    if is_insertion:
                        word = org_word

                    if is_c and is_d:
                        if word != self._do_replace(word, a_loc, a_loc + a_size, feature_to_type, feature_to_sounds):
                            word_types[i] = ExampleType.CADT
                            location = (a_loc, a_loc + a_size)

                            if word in self._CADT_indexes:
                                if location not in self._CADT_indexes[word]:
                                    self._CADT_indexes[word].append(location)
                            else:
                                self._CADT_indexes[word] = [location]
                        elif word_types[i] != ExampleType.CADT:
                            word_types[i] = ExampleType.CADNT

                    elif ExampleType.CADT != word_types[i] and ExampleType.CADNT != word_types[i]:
                        if is_c and not is_d:
                            word_types[i] = ExampleType.CAND
                        elif not is_c and is_d:
                            word_types[i] = ExampleType.NCAD

            return word_types

    def get_interest_phones(self, phonemes: List[Word], feature_to_type: Dict[str, str],
                            feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[Dict[str, str], List[str]]:
        a_matcher = self.get_a_matcher(phonemes, None, feature_to_sounds)

        if len(a_matcher) == 1 and str(a_matcher[0]) == '':
            return {}, []

        # TODO uncertain deletion rule poi
        if not self._B or self._B[2] != 0:
            dict_ = {}
            lst = [str(am) for am in a_matcher]
            lst.append('Ø')
            for am in lst:
                dict_[am] = 'Ø'

            return dict_, lst

        result = {}
        all_phones = set([])

        if len(a_matcher) == 0:
            raise ValueError("No matching A found in the phonemes!")

        for a_word in a_matcher:
            if len(a_word) > 1:
                raise NotImplementedError("Not supporting A size greater than 1")

            b_word = self._do_replace(a_word, 0, 1, feature_to_type, feature_to_sounds)
            all_phones.add(str(a_word))

            if not b_word.is_empty():
                all_phones.add(str(b_word))

            result[str(a_word)] = str(b_word)

        all_phones = list(all_phones)
        all_phones.sort(key=lambda x: Sound('', [])[x].get_num())
        return result, all_phones

    def locations_a(self, word: Word, phonemes: Optional[None, List[Word]],
                    feature_to_sounds: Dict[str, List[Sound]]) -> Dict[
        int, Word]:
        if self._As is None:
            dict_ = {}

            for i in range(0, len(word) + 1):
                dict_[i] = Word("")
            return dict_

        a_matcher = self.get_a_matcher(phonemes, None, feature_to_sounds)  # type:List[Word]
        if len(a_matcher) == 1 and str(a_matcher[0]) == '':
            result = {}

            for i in range(0, len(word) + 1):
                result[i] = Word('')
        else:
            prev_index = 0  # type: int
            result = {}  # type: Dict[int, Word]
            i = 0

            while i < len(a_matcher):
                a_pattern = a_matcher[i]
                a_index = word.index_in_word(a_pattern, prev_index)

                if a_index < 0:
                    i += 1
                    prev_index = 0
                    continue
                else:
                    prev_index = a_index + 1
                    result[a_index] = a_pattern
                    i -= 1

                i += 1

        return result

    def get_a_matcher(self, phonemes: Optional[None, List[Word]], size_limit: Optional[int, None],
                      feature_to_sounds: Dict[str, List[Sound]]) -> List[Word]:
        if not self._As:
            return [Word("")]

        a_matcher = []  # type: List[Word]
        for sec in self._As:
            words = Template(sec).generate_word_list(phonemes, size_limit, feature_to_sounds)
            a_matcher.extend(words)
        return a_matcher

    def get_c_matchers(self, phonemes: Optional[List[Word], None], feature_to_sounds: Dict[str, List[Sound]]) -> List[
        List[Word]]:
        c_matchers = []  # type: List[List[Word]]

        for c_ins in self._Cs:
            c_matchers.append(_get_c_instance_matcher(c_ins, phonemes, None, feature_to_sounds)[0])

        return c_matchers

    def get_d_matchers(self, phonemes: Optional[List[Word], None], feature_to_sounds: Dict[str, List[Sound]]) -> List[
        List[Word]]:
        d_matchers = []  # type: List[List[Word]]

        for d_ins in self._Ds:
            d_matchers.append(_get_d_instance_matcher(d_ins, phonemes, None, feature_to_sounds)[0])

        return d_matchers

    def get_rule_type(self, phonemes: List[Word], feature_to_type: Dict[str, str],
                      feature_to_sounds: Dict[str, List[Sound]]) -> RuleType:
        if self._B is None:
            return RuleType.Alternating
        elif self._B[2] != 0:
            return RuleType.Mixed

        has_alternating = False
        has_neutralizing = False

        a_matchers = self.get_a_matcher(phonemes, None, feature_to_sounds)

        for a in a_matchers:
            if self._do_replace(a, 0, 1, feature_to_type, feature_to_sounds) in phonemes:
                has_neutralizing = True
            else:
                has_alternating = True

        if has_alternating and not has_neutralizing:
            return RuleType.Alternating
        elif has_neutralizing and not has_alternating:
            return RuleType.Neutralizing
        else:
            return RuleType.Mixed

    def validate_cd(self, phonemes: Optional[List[Sound], None], feature_to_sounds: Dict[str, List[Sound]]) -> bool:
        for i in range(0, len(self._Cs)):
            if (self._Cs[i] is None or len(
                    _get_c_instance_matcher(self._Cs[i], phonemes, None, feature_to_sounds)[0]) > 0) and (
                    self._Ds[i] is None or len(
                _get_d_instance_matcher(self._Ds[i], phonemes, None, feature_to_sounds)[0]) > 0):
                return True
        return False

    def _do_replace(self, word: Word, begin_index: int, end_index: int, feature_to_type: Dict[str, str],
                    feature_to_sounds: Dict[str, List[Sound]]) -> Word:

        if end_index - begin_index > 1:
            raise NotImplementedError(
                "begin %d end %d type like this has not been implemented yet" % (begin_index, end_index))

        if self._B is None:
            return word.change_word(begin_index, end_index, None)
        else:
            dest_particle = self._B[0]
            ignored_types = self._B[1]
            copy_index = self._B[2]
            is_insertion = begin_index == end_index

            if copy_index == 0:
                if is_insertion:
                    raise ValueError("Cant't have non-copying rule with empty A - use PREDEFINED instead")

                if dest_particle is None:
                    raise ValueError("copy index 0 while no particle is given (Use None for deletion)")

                a_target = str(word[begin_index:end_index])
                dest_sound = Sound('', [])[a_target].get_transformed_sound(dest_particle, ignored_types,
                                                                           feature_to_type, feature_to_sounds)
            else:
                if dest_particle is None:
                    return word.change_word(begin_index, end_index,
                                            word[begin_index + copy_index:end_index + copy_index])
                if is_insertion:
                    env_target = str(word[begin_index + copy_index:end_index + copy_index + 1])
                else:
                    env_target = str(word[begin_index + copy_index:end_index + copy_index])

                if env_target == '' or len(env_target) == 0:
                    dest_sound = None
                else:
                    dest_sound = Sound('', [])[env_target].get_transformed_sound(dest_particle, ignored_types,
                                                                                 feature_to_type, feature_to_sounds)

            if dest_sound is not None:
                return word.change_word(begin_index, end_index, Word([dest_sound]))

        return word

    def get_name(self) -> str:
        return self._name

    def get_c_split_size(self) -> int:
        return len(self._Cs)

    def get_family(self) -> RuleFamily:
        return self._family

    def get_content_str(self) -> str:
        a_str = ''

        if self._As is not None:
            for sec in self._As:
                if len(a_str) > 0:
                    a_str += ' or '

                a_str += "".join(str(s) for s in sec)

        if self._B is None:
            b_str = ''
        else:
            b_str = "%s,%s" % (str(self._B[0]), str(self._B[1]))

        cd_str = ''

        for i in range(0, len(self._Cs)):
            if len(cd_str) > 0:
                cd_str += ' or '

            c_block = self._Cs[i]
            d_block = self._Ds[i]
            c_edge = self._Cs_edge[i]
            d_edge = self._Ds_edge[i]

            c_part = ''
            if c_edge:
                c_part += '#'
            if c_block is not None:
                c_part += "".join([str(s) for s in c_block])

            d_part = ''
            if d_block is not None:
                d_part += "".join([str(s) for s in d_block])
            if d_edge:
                d_part += '#'

            part = "%s _ %s" % (c_part, d_part)

            cd_str += part

        return "%s -> %s / %s" % (a_str, b_str, cd_str)

    def __str__(self) -> str:
        return "%s ===== %s" % (self._name, self.get_content_str())


class PredefinedRule(Rule):
    _AtoB: Dict[Word, Word]

    def __init__(self, name: str, family: RuleFamily, a_to_b: Dict[str, str],
                 c: List[Optional[List[Particle], None]], c_edge: List[bool], d: List[Optional[List[Particle], None]],
                 d_edge: List[bool]) -> None:
        Rule.__init__(self, name, family, [], None, c, c_edge, d, d_edge)

        self._AtoB = {}
        for key in a_to_b.keys():
            self._AtoB[Word(key)] = Word(a_to_b[key])

    def _do_replace(self, word: Word, begin_index: int, end_index: int, feature_to_type: Dict[str, str],
                    feature_to_sounds: Dict[str, List[Sound]]) -> Word:
        if end_index - begin_index > 1:
            raise NotImplementedError(
                "begin %d end %d type like this has not been implemented yet" % (begin_index, end_index))
        return word.change_word(begin_index, end_index, self._AtoB[word[begin_index:end_index]])

    def get_interest_phones(self, phonemes: List[Word], feature_to_type: Dict[str, str],
                            feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[Dict[str, str], List[str]]:
        a_to_b_str = {}  # type: Dict[str, str]
        interest_list = []  # type: List[str]
        for k in self._AtoB.keys():
            a_val = str(k)
            if len(a_val) == 0 or a_val.isspace() or a_val == '':
                a_val = 'Ø'

            b_val = str(self._AtoB[k])
            if len(b_val) == 0 or b_val.isspace() or b_val == '':
                b_val = 'Ø'
            interest_list.append(a_val)
            interest_list.append(b_val)
            a_to_b_str[a_val] = b_val

        return a_to_b_str, interest_list

    def get_a_matcher(self, phonemes: List[Word], size_limit: Optional[int, None],
                      feature_to_sounds: Dict[str, List[Sound]]) -> List[Word]:
        return list(self._AtoB.keys())

    def get_content_str(self) -> str:
        ab_str = ''

        for key in self._AtoB.keys():
            ab_str += "%s > %s, " % (key, self._AtoB[key])

        ab_str = ab_str.rstrip(', ')
        parent_str = Rule.get_content_str(self)

        return "<Predefined> {%s} %s" % (ab_str, parent_str[parent_str.index('/'):])


class RuleFamily(Serializable):
    _rules: List[Rule]
    _name: str

    def __init__(self, name: str, default: List[Rule]) -> None:
        self._rules = default
        self._name = name

    def add_rule(self, rule: Rule) -> bool:
        if rule not in self._rules:
            self._rules.append(rule)
            return True
        else:
            return False

    def get_rules(self) -> List[Rule]:
        return [r for r in self._rules]

    def get_name(self) -> str:
        return self._name

    def serialize(self, **kwargs):
        return self.get_name()

    def __str__(self) -> str:
        return "%s : %s" % (self._name, str([r.get_name() for r in self._rules]))


def import_default_rules(feature_pool: List[str]) -> Tuple[List[RuleFamily], List[Rule]]:
    import os
    return _fetch_rule_and_family_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/defaultrules.csv"),
                                      feature_pool)


def _fetch_rule_and_family_csv(filename: str, feature_pool: List[str]) -> Tuple[List[RuleFamily], List[Rule]]:
    rules = []  # type: List[Rule]
    families = {}  # type: Dict[str, RuleFamily]

    with open(filename, encoding='utf-8', newline='') as data_file:
        lines = csv.reader(data_file)

        for line in lines:
            if len(line) == 0 or len(line[0]) == 0 or line[0] == '' or str(line[0]).startswith('\ufeff'):
                continue

            line = [str(s).replace('ɡ', 'g') for s in line]

            family_name = line[2]

            if family_name not in families.keys():
                families[family_name] = RuleFamily(family_name, [])

            rule_family = families[family_name]
            rule_name = line[1]
            rule_content = str(line[0]).strip().strip('\n').strip('\ufeff')

            rule = interpret_rule_content_str(rule_content, feature_pool, rule_name, rule_family)

            rule_family.add_rule(rule)
            rules.append(rule)

    return list(families.values()), rules


def interpret_rule_content_str(rule_content: str, feature_pool: List[str], rule_name: str,
                               rule_family: Optional[RuleFamily, None]) -> Rule:
    import ast
    if rule_content.startswith('<<PREDEFINED>>'):
        predefined = True
        rule_content = rule_content[14:]
    else:
        predefined = False

    mid_break = rule_content.split("/")

    cd_info = _interpret_cd(mid_break[1], feature_pool)

    if predefined:
        rule = PredefinedRule(rule_name, rule_family, ast.literal_eval(mid_break[0]), cd_info[0], cd_info[1],
                              cd_info[2], cd_info[3])
    else:
        action_break = mid_break[0].split(">")

        if len(action_break) != 2:
            raise ImportError("Invalid rule format: %s" % rule_content)

        a_str = action_break[0]
        b_str = action_break[1]

        if len(b_str) == 0 or b_str[0] == '0':
            b_sec = None
        elif b_str[0] == '[' and b_str[-1] == ']':
            b_sec = _interpret_b(b_str.lstrip('[').rstrip(']'), feature_pool)
        else:
            raise ValueError("error reading b data invalid format %s" % b_str)

        if len(mid_break) != 2:
            raise ImportError("Invalid rule format: %s" % rule_content)

        rule = Rule(rule_name, rule_family, _interpret_a(a_str, feature_pool), b_sec, cd_info[0],
                    cd_info[1], cd_info[2], cd_info[3])

    return rule


def _interpret_b(b_str: str, feature_pool: List[str]) -> Tuple[Optional[Particle, None], List[str], int]:
    var_count = b_str.count('$')

    if var_count > 0:
        if var_count != 2:
            raise ValueError("B var env not met. Ex. [$...$...]")

        var_end_index = b_str.index('$', 1)
        copy_loc = int(b_str[1:var_end_index])
        b_data = b_str[var_end_index + 1:].split(",")
    else:
        copy_loc = 0
        b_data = b_str.split(",")

    if len(b_data) == 1 and (b_data[0] == '' or len(b_data[0]) == 0):
        return None, [], copy_loc

    particle_data = []  # type: List[str]
    ignored_types = []  # type: List[str]

    for data in b_data:
        if data.startswith("(") and data.endswith(")"):
            ignored_types.append(data.lstrip("(").rstrip(")"))
        else:
            if data not in feature_pool:
                raise ValueError("error reading b data, particle \"%s\" is undefined in %s" % (data, b_str))

            particle_data.append(data)

    return Particle(particle_data, False), ignored_types, copy_loc


def _interpret_a(a_str: str, feature_pool: List[str]) -> Optional[None, List[List[Particle]]]:
    if len(a_str) == 0:
        return None

    conditions = a_str.split("&")
    a_list = []  # type: List[List[Particle]]

    for cond_sec in conditions:
        a_list.append(_sec_to_particles(feature_pool, cond_sec))

    return a_list


def _interpret_cd(cd_str: str, feature_pool: List[str]) -> Tuple[
    List[Optional[List[Particle], None]], List[bool], List[Optional[List[Particle], None]], List[bool]]:
    conditions = cd_str.split("&")
    c_list = []  # type: List[Optional[List[Particle], None]]
    d_list = []  # type: List[Optional[List[Particle], None]]
    c_edge = []  # type: List[bool]
    d_edge = []  # type: List[bool]

    for cond_sec in conditions:
        condition_break = cond_sec.split("_")

        if len(condition_break) != 2:
            raise ImportError("Invalid rule format: %s" % cond_sec)

        c_part = condition_break[0]
        d_part = condition_break[1]

        if len(c_part) > 0 and c_part[0] == EDGE_SYMBOL:
            c_part = c_part[1:]
            c_edge.append(True)
        else:
            c_edge.append(False)

        if len(d_part) > 0 and d_part[-1] == EDGE_SYMBOL:
            d_part = d_part[:len(d_part) - 1]
            d_edge.append(True)
        else:
            d_edge.append(False)

        c_list.append(_sec_to_particles(feature_pool, c_part))
        d_list.append(_sec_to_particles(feature_pool, d_part))

    return c_list, c_edge, d_list, d_edge


def _sec_to_particles(feature_pool: List[str], sec: str) -> Optional[List[Particle], None]:
    particles = []  # type: List[Particle]

    parts = sec.lstrip('[').rstrip(']').split("][")

    if len(parts) == 1 and len(parts[0]) == 0:
        return None

    for part in parts:
        is_replicated = False
        if part[0] == '*':
            is_replicated = True
            part = part[1:]

        features = part.split(",")

        for feature in features:
            if feature.lstrip("!") not in feature_pool:
                raise ImportError(
                    "Rule sector %s with feature %s does not conform to the given features." % (sec, feature))

        particles.append(Particle(features, is_replicated))

    return particles
