from __future__ import annotations

import logging
import random
import time
from enum import IntEnum
from typing import List, Tuple, Dict, Optional, Any, Set

from script import Word, Rule, ExampleType, Sound, Template, GlossGroup

WORD_POOL_DEFAULT_SIZE = 300
IRR_PERCENTAGE = 0.1
RELATED_PERCENTAGE = 0.9
SPLIT_REFILL_RETRY_LIMIT = 5
EXCLUSION_TYPES = [ExampleType.CADT, ExampleType.CADNT]
LOGGER = logging.getLogger("app.logger")


class GenMode(IntEnum):
    rawData = 0,
    IPAg = 1,
    nIPAg = 2,
    isolateGloss = 3


class Generator:
    _difficulty: int  # 0- 10
    _difficulty_to_percent: Dict[int, Tuple[float, float, float, float, float]]
    _templates: List[Template]
    _rule: Rule
    _phonemes: List[Word]
    _CADT: List[Set[Word]]
    _CADNT: List[Set[Word]]
    _CAND: List[Set[Word]]
    _NCAD: List[Set[Word]]
    _IRR: List[Set[Word]]
    _duplicate_exclusion: Set[Word]
    _feature_to_type: Dict[str, str]
    _feature_to_sounds: Dict[str, List[Sound]]
    _unid: int

    def __init__(self, phonemes: List[Word], templates: List[Template], rule: Rule, difficulty: int,
                 _feature_to_type: Dict[str, str], _feature_to_sounds: Dict[str, List[Sound]], **kwargs) -> None:
        self._templates = templates
        self._rule = rule
        self._feature_to_type = _feature_to_type
        self._feature_to_sounds = _feature_to_sounds
        self._CADT = [set([]) for _ in range(rule.get_c_split_size())]
        self._CADNT = [set([]) for _ in range(rule.get_c_split_size())]
        self._CAND = [set([]) for _ in range(rule.get_c_split_size())]
        self._NCAD = [set([]) for _ in range(rule.get_c_split_size())]
        self._IRR = [set([]) for _ in range(rule.get_c_split_size())]
        self._duplicate_exclusion = set([])
        self._phonemes = phonemes
        self._unid = random.getrandbits(20) + int(round(time.time() * 1000.0))

        self._difficulty_to_percent = {
            5: (0.4, 0.1, 0.2, 0.2, 0.1)
        }

        special_interests = kwargs.get('special_interests', None)  # type: Optional[None, List[Word]]

        self._difficulty = difficulty
        LOGGER.debug("Rule size: %d" % self._rule.get_c_split_size())
        self._expand_library(WORD_POOL_DEFAULT_SIZE, special_interests=special_interests)

    def _expand_library(self, pool_size: int, **kwargs):
        template_pool_size = pool_size / len(self._templates)
        generation_summary = {ExampleType.CADT: 0, ExampleType.CADNT: 0, ExampleType.CAND: 0, ExampleType.NCAD: 0,
                              ExampleType.IRR: 0}
        a_matcher = self._rule.get_a_matcher(self._phonemes, None, self._feature_to_sounds)
        cd_validated = self._rule.validate_cd(self._phonemes, self._feature_to_sounds)
        special_interests = kwargs.get('special_interests', None)  # type: Optional[None, List[Word]]

        if len(a_matcher) == 0 or a_matcher == [] or not cd_validated:
            raise GenerationNoCADTError(self)

        is_insertion = False
        if len(a_matcher) == 1 and str(a_matcher[0]) == '':
            is_insertion = True

        if is_insertion:
            irr_size = 0
            related_size = template_pool_size

            irr_phoneme = []
        else:
            irr_size = round(template_pool_size * IRR_PERCENTAGE)
            related_size = round(template_pool_size * RELATED_PERCENTAGE)

            irr_phoneme = [w for w in self._phonemes if w not in a_matcher]

        for template in self._templates:
            if irr_size > 0:
                irr_word_list = template.generate_word_list(irr_phoneme, irr_size, self._feature_to_sounds)
                random.shuffle(irr_word_list)
            else:
                irr_word_list = []

            if special_interests is None:
                if is_insertion:
                    related_word_list = template.generate_word_list(self._phonemes, related_size,
                                                                    self._feature_to_sounds)
                else:
                    related_word_list = template.generate_word_list(self._phonemes, related_size,
                                                                    self._feature_to_sounds,
                                                                    primary_interest=a_matcher)
            else:
                related_word_list = template.generate_word_list(self._phonemes, related_size, self._feature_to_sounds,
                                                                primary_interest=a_matcher,
                                                                secondary_interest=special_interests)

            # RELATED

            for word in related_word_list:
                word_types = self._rule.classify(word, self._phonemes, self._feature_to_type, self._feature_to_sounds)

                for index in range(0, len(word_types)):
                    word_type = word_types[index]

                    if ExampleType.IRR == word_type:
                        raise GeneratorError(self, "Related word list should never have IRR type. "
                                                   "Related word list: %s || Word: %s" % (
                                                 [str(w) for w in related_word_list], word))

                    if ExampleType.CADT == word_type:
                        self._CADT[index].add(word)
                        generation_summary[ExampleType.CADT] += 1
                        break

                    if ExampleType.CADNT == word_type:
                        self._CADNT[index].add(word)
                        generation_summary[ExampleType.CADNT] += 1

                    if ExampleType.CAND == word_type:
                        self._CAND[index].add(word)
                        generation_summary[ExampleType.CAND] += 1

                    if ExampleType.NCAD == word_type:
                        self._NCAD[index].add(word)
                        generation_summary[ExampleType.NCAD] += 1

            # IRR
            for word in irr_word_list:
                generation_summary[ExampleType.IRR] += 1

                for index in range(0, len(self._IRR)):
                    self._IRR[index].add(word)

    def get_difficulty(self) -> int:
        return self._difficulty

    def get_templates(self) -> List[Template]:
        return [t for t in self._templates]

    def get_phonemes(self) -> List[Word]:
        return self._phonemes

    def get_rule(self) -> Rule:
        return self._rule

    def change_difficulty(self, target_difficulty: int) -> None:
        self._difficulty = target_difficulty

    def _get_num(self, amount: int) -> Tuple[int, int, int, int, int]:
        diff_data = self._difficulty_to_percent[self._difficulty]
        cadt = round(amount * diff_data[0])
        cadnt = round(amount * diff_data[1])
        cand = round(amount * diff_data[2])
        ncad = round(amount * diff_data[3])
        irr = round(amount * diff_data[4])

        total_num = cadt + cadnt + cand + ncad + irr

        if total_num > amount:
            irr -= total_num - amount

        if total_num < amount:
            cadt += amount - total_num

        return cadt, cadnt, cand, ncad, irr

    def _generate_helper(self, word_bank: Set[Word], amount: int, name: str) -> List[Word]:
        if amount == 0:
            return []

        bank_size = len(word_bank)

        if bank_size == 0:
            LOGGER.debug("No %s type found.(%d required, 0 found)\n" % (name, amount))
            return []

        if bank_size >= amount:
            count = 0
            words = []
            for word in word_bank:
                if word not in self._duplicate_exclusion:
                    words.append(word)
                    self._duplicate_exclusion.add(word)
                    count += 1

                if count >= amount:
                    break

            if len(words) < amount:
                self._expand_library(WORD_POOL_DEFAULT_SIZE)
                return self._generate_helper(word_bank, amount, name)
            else:
                return words
        else:
            LOGGER.debug(
                "Insufficient amount of %s type.(%d required, %d found), expanding library\n" % (
                    name, amount, bank_size))
            self._expand_library(WORD_POOL_DEFAULT_SIZE)
            return self._generate_helper(word_bank, amount, name)

    def get_log_stamp(self):
        return "%s \n %s \n %s \n @%d" % (
            str(self._rule), [str(w) for w in self._phonemes], [str(t) for t in self._templates], self._unid)

    def generate(self, gen_mode: GenMode, amount: Optional[int, List[int]], is_fresh: bool, is_shuffled: bool,
                 gloss_groups: Optional[None, List[GlossGroup]]) -> Optional[Dict[str, Any], None]:
        if is_fresh:
            self._duplicate_exclusion = set([])

        ur_words = []  # type: List[Word]
        sr_words = []  # type: List[Word]
        generation_amounts = [0, 0, 0, 0, 0]  # type: List[int]
        split_size = len(self._CADT)
        cadt_extra = -1

        if type(amount) == int:
            total_amount = amount
            cadt_num, cadnt_num, cand_num, ncad_num, irr_num = self._get_num(round(amount / split_size))
        elif type(amount) == list:
            if len(amount) == 2:
                normal_amount = amount[0]
                cadt_extra = amount[1]
                cadt_num, cadnt_num, cand_num, ncad_num, irr_num = self._get_num(round(normal_amount / split_size))
                cadt_num += cadt_extra
                total_amount = normal_amount + cadt_extra
            elif len(amount) != 5 or False in [type(i) == int for i in amount]:
                raise GeneratorParameterError(self, amount, "amount given in list should be in format int[5] > 0")
            else:
                cadt_num, cadnt_num, cand_num, ncad_num, irr_num = amount[0], amount[1], amount[2], amount[
                    3], amount[4]
                total_amount = sum(amount)

        else:
            raise GeneratorParameterError(self, amount, "amount must be either int list or int")

        LOGGER.info("A matchers: %s  CD matchers: %s\n" % (
            [str(w) for w in self._rule.get_a_matcher(self._phonemes, None, self._feature_to_sounds)],
            ["%s_%s  " % ([str(wc) for wc in c], [str(wd) for wd in d])
             for c in self._rule.get_c_matchers(self._phonemes, self._feature_to_sounds)
             for d in self._rule.get_d_matchers(self._phonemes, self._feature_to_sounds)]
        ))
        LOGGER.info("REQUEST: PIECES %d CADT %d CADNT %d CAND %d NCAD %d IRR %d\n%s\n" % (
            split_size, cadt_num, cadnt_num, cand_num, ncad_num, irr_num, self.get_log_stamp()))

        failed_indexes = set([])
        fill_retry_count = 0
        index = 0
        cadt_words = []  # type: List[Word]
        cadnt_words = []  # type: List[Word]
        cand_words = []  # type: List[Word]
        ncad_words = []  # type: List[Word]
        irr_words = []  # type: List[Word]
        while index < split_size:

            if fill_retry_count > SPLIT_REFILL_RETRY_LIMIT:
                raise GeneratorError(self, "Some index does not produce result, while refilling failed for "
                                           "unknown reason! Required %d Current %d\n" % (total_amount, len(ur_words)))

            if index in failed_indexes:
                index += 1
                continue

            cadt_gen = self._generate_helper(self._CADT[index], cadt_num, "CADT")
            cadnt_gen = self._generate_helper(self._CADNT[index], cadnt_num, "CADNT")
            cand_gen = self._generate_helper(self._CAND[index], cand_num, "CAND")
            ncad_gen = self._generate_helper(self._NCAD[index], ncad_num, "NCAD")
            irr_gen = self._generate_helper(self._IRR[index], irr_num, "IRR")

            # FINISH RANDOM PICK
            cadt_res, cadnt_res, cand_res, ncad_res, irr_res = len(cadt_gen), len(cadnt_gen), len(
                cand_gen), len(ncad_gen), len(irr_gen)

            LOGGER.debug("1ST GET: PCS_INDEX %d CADT %d CADNT %d CAND %d NCAD %d IRR %d\n" % (
                index, len(cadt_gen), len(cadnt_gen), len(cand_gen), len(ncad_gen), len(irr_gen)))

            if cadt_res == 0 and cadt_num > 0:
                LOGGER.warning("Condition Index %d in rule %s does not have any related data\n" % (index, self._rule))
                failed_indexes.add(index)
                index = 0
                continue

            if irr_res == 0 and irr_num > 0:
                cadt_gen.extend(
                    self._generate_helper(self._CADT[index], irr_num, "CADT"))

            if cadnt_res == 0 and cadnt_num > 0:
                cadt_gen.extend(
                    self._generate_helper(self._CADT[index], cadnt_num, "CADT"))

            if cand_res == 0 and cand_num > 0:
                if ncad_res == 0:
                    cadt_gen.extend(
                        self._generate_helper(self._CADT[index], cand_num, "CADT"))
                else:
                    ncad_gen.extend(self._generate_helper(self._NCAD[index], cand_num, "NCAD"))

            if ncad_res == 0 and ncad_num > 0:
                if cand_res == 0:
                    cadt_gen.extend(self._generate_helper(self._CADT[index], ncad_num, "CADT"))
                else:
                    cand_gen.extend(self._generate_helper(self._CAND[index], ncad_num, "CAND"))

            LOGGER.debug("2ND GET: PCS_INDEX %d CADT %d CADNT %d CAND %d NCAD %d IRR %d\n" % (
                index, len(cadt_gen), len(cadnt_gen), len(cand_gen), len(ncad_gen), len(irr_gen)))

            generation_amounts[0] += len(cadt_gen)
            generation_amounts[1] += len(cadnt_gen)
            generation_amounts[2] += len(cand_gen)
            generation_amounts[3] += len(ncad_gen)
            generation_amounts[4] += len(irr_gen)

            cadt_words.extend(cadt_gen)
            cadnt_words.extend(cadnt_gen)
            cand_words.extend(cand_gen)
            ncad_words.extend(ncad_gen)
            irr_words.extend(irr_gen)

            amount_generated = len(cadt_words) + len(cadnt_words) + len(cand_words) + len(ncad_words) + len(irr_words)

            index += 1

            if index >= split_size and amount_generated < total_amount:
                index = 0
                fill_retry_count += 1

        if gen_mode == GenMode.rawData:
            LOGGER.debug("GenMode 0 - raw data")
            return {"CADT": cadt_words, "CADNT": cadnt_words, "CAND": cand_words, "NCAD": ncad_words, "IRR": irr_words}
        elif gloss_groups is None:
            raise ValueError("If GenMode is not 0 - raw data, then gloss group must be present.")

        if cadt_extra > 0:
            ur_words = cadt_words[cadt_extra:] + cadnt_words + cand_words + ncad_words + irr_words + cadt_words[
                                                                                                     :cadt_extra]
        else:
            ur_words = cadt_words + cadnt_words + cand_words + ncad_words + irr_words

        if len(ur_words) == 0 and len(failed_indexes) == split_size:
            raise GeneratorError(self, "All indexes failed! No result can be produced. \n%s\n" % self.get_log_stamp())

        if is_shuffled:
            random.shuffle(ur_words)

        for word in ur_words:
            sr_words.append(self._rule.apply(word, self._phonemes, self._feature_to_type, self._feature_to_sounds)[0])

        gloss_words = [w.pick() for w in random.sample(gloss_groups, len(ur_words))]

        phones_of_interest = self._rule.get_interest_phones(self._phonemes, self._feature_to_type,
                                                            self._feature_to_sounds)[1]

        # filter obscene words
        appropriate_ur = []
        appropriate_sr = []
        appropriate_gloss = []
        for i in range(len(ur_words)):
            if ur_words[i].is_appropriate() and sr_words[i].is_appropriate():
                appropriate_ur.append(ur_words[i])
                appropriate_sr.append(sr_words[i])
                appropriate_gloss.append(gloss_words[i])
        ur_words = appropriate_ur
        sr_words = appropriate_sr
        gloss_words = appropriate_gloss

        if gen_mode == GenMode.IPAg:
            LOGGER.debug("Gen Mode 1 - str ipa g mode")
            return {"UR": [str(w).replace('g', 'ɡ') for w in ur_words],
                    "SR": [str(w).replace('g', 'ɡ') for w in sr_words],
                    "Gloss": [str(w) for w in gloss_words],
                    "rule": str(self._rule),
                    "templates": [str(w) for w in self._templates],
                    "phonemes": [str(w).replace('g', 'ɡ') for w in self._phonemes],
                    "phone_interest": [str(w).replace('g', 'ɡ') for w in phones_of_interest]}
        elif gen_mode == GenMode.nIPAg:
            LOGGER.debug("Gen Mode 2 - str non ipa g mode")
            return {"UR": [str(w) for w in ur_words],
                    "SR": [str(w) for w in sr_words],
                    "Gloss": [str(w) for w in gloss_words],
                    "rule": str(self._rule),
                    "templates": [str(w) for w in self._templates],
                    "phonemes": [str(w) for w in self._phonemes],
                    "phone_interest": [str(w) for w in phones_of_interest]}
        elif gen_mode == GenMode.isolateGloss:
            LOGGER.debug("Gen Mode 3 - org mode")
            return {"UR": ur_words, "SR": sr_words, "Gloss": gloss_words, "rule": self._rule,
                    "templates": self._templates,
                    "phonemes": self._phonemes, "phone_interest": phones_of_interest}
        else:
            raise NotImplementedError("GenMode provided is not implemented")


class GeneratorError(Exception):
    def __init__(self, generator: Generator, message: str) -> None:
        super(GeneratorError, self).__init__("%s \n %s\n" % (message, generator.get_log_stamp()))


class GeneratorParameterError(GeneratorError):
    def __init__(self, generator: Generator, bad_param: Any, message: str) -> None:
        super(GeneratorParameterError, self).__init__(generator, "%s Got: %s" % (message, str(bad_param)))


class GenerationNoCADTError(GeneratorError):
    def __init__(self, generator: Generator) -> None:
        super(GenerationNoCADTError, self).__init__(generator, "No CADT found with associated phoneme!")
