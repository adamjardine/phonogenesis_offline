from __future__ import annotations

import logging
import random
from abc import ABCMeta, abstractmethod
from enum import Enum, IntEnum
from typing import List, Dict

from script import Word, Rule, Sound, Template, Generator, GenMode
from serializable import Serializable

LOGGER = logging.getLogger("app.logger")


class InteractionOrder(Enum):
    Feeding = 0,
    Bleeding = 1,
    CounterFeeding = 2,
    CounterBleeding = 3

    def __str__(self) -> str:
        return self.name


class DoubleWordDifficulty(Enum):
    Easy = 0,
    Harder = 1,
    Hardest = 2

    def __str__(self) -> str:
        return self.name


class DoubleWordType(IntEnum):
    """
    • apply rule2 to UR, count how many changes it makes (X)
    • apply rule1 to UR, count how many changes it makes (Y)
    • apply rule2 to output of rule1(UR), count how many changes it makes (Z)

    Then:
    if X=Z=0 and Y>0, this is rule1 only (your Type 1)
    if X=Z>0 and Y=0, this is rule2 only (your Type 2)
    if X<Z and Y>0, this is both rules with feeding (your Type 0)
    if X=Z>0 and Y>0, this is both rules without feeding (a mix of Type 1 and Type 2, call it Type 3)
    if X=Z=0 and Y=0, this is neither rule (your Type 4)

    """
    Type0 = 0,
    Type1 = 1,
    Type2 = 2,
    Type3 = 3,
    Type4 = 4

    def __str__(self) -> str:
        return self.name


class DoubleRule(Serializable, metaclass=ABCMeta):
    _rule1: Rule
    _rule2: Rule
    _difficulty: DoubleWordDifficulty
    _interactOrder: InteractionOrder
    _phonemes: List[Word]
    _templates: List[Template]
    _feature_to_type: Dict[str, str]
    _feature_to_sounds: Dict[str, List[Sound]]

    def __init__(self, rule1: Rule, rule2: Rule, order: InteractionOrder, is_counter: bool,
                 difficulty: DoubleWordDifficulty, phonemes: List[Word], templates: List[Template],
                 feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]]) -> None:
        self._rule1 = rule1
        self._rule2 = rule2
        self._difficulty = difficulty
        self._phonemes = phonemes
        self._feature_to_type = feature_to_type
        self._feature_to_sounds = feature_to_sounds
        self._templates = templates

        if is_counter:
            if order == InteractionOrder.Feeding:
                self._interactOrder = InteractionOrder.CounterFeeding
            elif order == InteractionOrder.Bleeding:
                self._interactOrder = InteractionOrder.CounterBleeding
            else:
                self._interactOrder = order
        else:
            self._interactOrder = order

    @abstractmethod
    def generate(self, amount: int):
        raise NotImplementedError

    @abstractmethod
    def get_word_type(self, word: Word) -> DoubleWordType:
        raise NotImplementedError

    def serialize(self, **kwargs):
        raise NotImplementedError

    def get_difficulty(self) -> DoubleWordDifficulty:
        return self._difficulty

    def get_rule1(self) -> Rule:
        return self._rule1

    def get_rule2(self) -> Rule:
        return self._rule2

    def get_order(self) -> InteractionOrder:
        return self._interactOrder


class DoubleFeed(DoubleRule):
    """
    • apply rule2 to UR, count how many changes it makes (X)
    • apply rule1 to UR, count how many changes it makes (Y)
    • apply rule2 to output of rule1(UR), count how many changes it makes (Z)

    Then:
    if X=Z=0 and Y>0, this is rule1 only (your Type 1)
    if X=Z>0 and Y=0, this is rule2 only (your Type 2)
    if X<Z and Y>0, this is both rules with feeding (your Type 0)
    if X=Z>0 and Y>0, this is both rules without feeding (a mix of Type 1 and Type 2, call it Type 3)
    if X=Z=0 and Y=0, this is neither rule (your Type 4)

    """
    _gen2: Generator
    _gen1: Generator

    def __init__(self, rule1: Rule, rule2: Rule, order: InteractionOrder, is_counter: bool,
                 difficulty: DoubleWordDifficulty, phonemes: List[Word], templates: List[Template],
                 feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]]) -> None:
        DoubleRule.__init__(self, rule1, rule2, order, is_counter, difficulty, phonemes, templates, feature_to_type,
                            feature_to_sounds)

        self._gen2 = Generator(phonemes, templates, rule2, 5, feature_to_type, feature_to_sounds,
                               special_interests=rule1.get_a_matcher(phonemes, None, feature_to_sounds))
        self._gen1 = Generator(phonemes, templates, rule1, 5, feature_to_type, feature_to_sounds,
                               special_interests=rule2.get_a_matcher(phonemes, None, feature_to_sounds))

    def serialize(self, **kwargs):
        return {
            "rule1": self.get_rule1().serialize(),
            "rule2": self.get_rule2().serialize(),
            "order": str(InteractionOrder.Feeding)
        }

    def get_word_type(self, word: Word) -> DoubleWordType:
        word2, ct2 = self._rule2.apply(word, self._phonemes, self._feature_to_type, self._feature_to_sounds)
        word1, ct1 = self._rule1.apply(word, self._phonemes, self._feature_to_type, self._feature_to_sounds)
        word2to1, ct2to1 = self._rule2.apply(word1, None, self._feature_to_type, self._feature_to_sounds)

        if ct2 == ct2to1 == 0 and ct1 > 0:
            return DoubleWordType.Type1

        if ct2 == ct2to1 > 0 and ct1 == 0:
            return DoubleWordType.Type2

        if ct2 < ct2to1 and ct1 > 0:
            return DoubleWordType.Type0

        if ct2 == ct2to1 > 0 and ct1 > 0:
            return DoubleWordType.Type3

        if ct2 == ct2to1 == 0 and ct1 == 0:
            return DoubleWordType.Type4

        raise TypeError("Unidentified double word type with ct2 %d, ct1 %d, ct2to1 %d" % (ct2, ct1, ct2to1))

    def _gen_data(self) -> Dict[DoubleWordType, List[Word]]:
        result = {DoubleWordType.Type0: [], DoubleWordType.Type1: [], DoubleWordType.Type2: [],
                  DoubleWordType.Type3: [], DoubleWordType.Type4: []}
        data2 = self._gen2.generate(GenMode.rawData, 50, False, False, None)
        data1 = self._gen1.generate(GenMode.rawData, 50, False, False, None)

        words2 = data2["CADT"] + data2["CADNT"] + data2["CAND"] + data2["NCAD"] + data2["IRR"]
        words1 = data1["CADT"] + data1["CADNT"] + data1["CAND"] + data1["NCAD"] + data1["IRR"]

        for word in words2:
            type_ = self.get_word_type(word)
            result[type_].append(word)

        for word in words1:
            type_ = self.get_word_type(word)
            result[type_].append(word)

        return result

    def generate(self, amount: int):
        """
        BLOCK A - TYPE 0
        BLOCK B - TYPE 1
        BLOCK C - TYPE 2
        BLOCK D - 50% TYPE 3 50% TYPE 0
        """

        blockA_words = []  # type: List[Word]
        blockB_words = []  # type: List[Word]
        blockC_words = []  # type: List[Word]
        blockD_words = []  # type: List[Word]

        if self.get_difficulty() == DoubleWordDifficulty.Hardest:
            amt_blockA = round(amount * 0.25)
            amt_blockB = round(amount * 0.25)
            amt_blockC = round(amount * 0.25)
            amt_blockD = amount - amt_blockA - amt_blockB - amt_blockC
            amt_blockD3 = round(amt_blockD / 2.0)
            amt_blockD0 = amt_blockD - amt_blockD3
        else:
            amt_blockA = round(amount * 0.333)
            amt_blockB = round(amount * 0.333)
            amt_blockC = round(amount * 0.333)
            amt_blockD3 = 0
            amt_blockD0 = 0

        recur_lim = 3
        while recur_lim > 0:
            need_regen = False
            gen_data = self._gen_data()

            # BLOCK D
            while amt_blockD3 > 0 and amt_blockD0 > 0:
                if len(gen_data[DoubleWordType.Type3]) == 0 and len(gen_data[DoubleWordType.Type0]) == 0:
                    LOGGER.warning("Insufficient block D, forcing regen")
                    need_regen = True
                    break

                i = 0
                for i in range(min(len(gen_data[DoubleWordType.Type3]), max(amt_blockD3, amt_blockD0))):
                    blockD_words.append(gen_data[DoubleWordType.Type3].pop(0))
                amt_blockD3 -= i + 1

                i = 0
                for i in range(min(len(gen_data[DoubleWordType.Type1]), max(amt_blockD3, amt_blockD0))):
                    blockD_words.append(gen_data[DoubleWordType.Type1].pop(0))
                amt_blockD0 -= i + 1

            random.shuffle(blockD_words)

            # BLOCK A
            i = 0
            for i in range(min(len(gen_data[DoubleWordType.Type0]), amt_blockA)):
                blockA_words.append(gen_data[DoubleWordType.Type0].pop(0))
            amt_blockA -= i + 1

            if amt_blockA > 0:
                LOGGER.warning("Insufficient block A from type 0, forcing regen!")
                need_regen = True

            # BLOCK B
            i = 0
            for i in range(min(len(gen_data[DoubleWordType.Type1]), amt_blockB)):
                blockB_words.append(gen_data[DoubleWordType.Type1].pop(0))
            amt_blockB -= i + 1

            if amt_blockB > 0:
                LOGGER.warning("Insufficient Type 1 in block B, using Type 3 as filler.")
                i = 0
                for i in range(min(len(gen_data[DoubleWordType.Type3]), amt_blockB)):
                    blockB_words.append(gen_data[DoubleWordType.Type3].pop(0))
                amt_blockB -= i + 1

            if amt_blockB > 0:
                LOGGER.warning("Insufficient block B from type 1 and type 3, forcing regen!")
                need_regen = True

            # BLOCK C
            i = 0
            for i in range(min(len(gen_data[DoubleWordType.Type2]), amt_blockC)):
                blockC_words.append(gen_data[DoubleWordType.Type2].pop(0))
            amt_blockC -= i + 1

            if amt_blockC > 0:
                LOGGER.warning("Insufficient Type 1 in block B, using Type 3 as filler.")
                i = 0
                for i in range(min(len(gen_data[DoubleWordType.Type3]), amt_blockC)):
                    blockC_words.append(gen_data[DoubleWordType.Type3].pop(0))
                amt_blockC -= i + 1

            if amt_blockC > 0:
                LOGGER.warning("Insufficient block B from type 1 and type 3, forcing regen!")
                need_regen = True

            if need_regen:
                recur_lim -= 1
            else:
                break

        if recur_lim <= 0:
            LOGGER.error("Reached maximum regen limit. Insufficient data generated.")

        return blockA_words, blockB_words, blockC_words, blockD_words
