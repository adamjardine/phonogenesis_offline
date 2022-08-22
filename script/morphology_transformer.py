from __future__ import annotations

from typing import List, Dict, Optional, Tuple, Union
from script import Rule, import_default_gloss, Template, Word, Sound
from abc import ABC, abstractmethod


def make_transformer(affix_type: str, mod_word: Optional[Word]):
    """
    Construct a transformer class of certain affix type based on the input "affix_type".
    """
    if affix_type == "SUFFIX":
        return SuffixTransformer(mod_word)
    elif affix_type == "PREFIX":
        return PrefixTransformer(mod_word)
    else:
        print("Wrong type of affix requested. By default, suffix transformer is called.")
        return SuffixTransformer(mod_word)


class Transformer(ABC):

    def __init__(self, mod_word):
        self._mod_word = mod_word

    @abstractmethod
    def get_mod_word(self) -> Word:
        return self._mod_word

    @abstractmethod
    def transform(self, word: Word) -> Word:
        raise NotImplementedError

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class SuffixTransformer(Transformer):
    def __init__(self, mod_word):
        super(SuffixTransformer, self).__init__(mod_word)

    def get_mod_word(self) -> Word:
        return super(SuffixTransformer, self).get_mod_word()

    def transform(self, word: Word) -> Word:
        if not self._mod_word:
            return word
        return Word(str(word) + str(self._mod_word))

    def __str__(self) -> str:
        if self._mod_word:
            return '+ ' + str(self._mod_word)
        else:
            return '+∅'


class PrefixTransformer(Transformer):
    def __init__(self, mod_word):
        super(PrefixTransformer, self).__init__(mod_word)

    def get_mod_word(self) -> Word:
        return super(PrefixTransformer, self).get_mod_word()

    def transform(self, word: Word) -> Word:
        if not self._mod_word:
            return word
        return Word(str(self._mod_word) + str(word))

    def __str__(self) -> str:
        if self._mod_word:
            return str(self._mod_word) + ' +'
        else:
            return '∅+'
