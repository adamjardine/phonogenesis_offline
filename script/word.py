from __future__ import annotations

import itertools
import logging
import os
from typing import List, Optional

from script.sound import Sound, _SYMBOL
from serializable import Serializable

LOGGER = logging.getLogger("app.logger")


class Word(Serializable):
    _sounds: List[Sound]

    def __init__(self, data: Optional[List[Sound], str]) -> None:

        if type(data) == str:
            sounds = []
            if len(data) == 1:
                sounds.append(_SYMBOL[data])
            else:
                i = 0

                while i < len(data):
                    end_loc = -1

                    for j in range(i + 1, len(data) + 1):
                        if len(data[i:j]) > 0 and data[i:j] in _SYMBOL:
                            end_loc = j
                    try:
                        sounds.append(_SYMBOL[data[i:end_loc]])
                    except KeyError as e:
                        continue
                    i = end_loc

            self._sounds = sounds

        elif type(data) == list and (len(data) == 0 or type(data[0]) == Sound):
            self._sounds = data
        else:
            raise TypeError("data must be either sound list or string, get %s" % str(type(data)))

    def serialize(self, **kwargs):
        return str(self)

    def get_sounds(self) -> List[Sound]:
        return self._sounds

    def reverse(self) -> Word:
        return Word(self._sounds[::-1])

    def change_word(self, begin_index: int, end_index: int, target: Optional[None, Word]) -> Word:
        """
        Build a new word with current word's given index replaced with target word.
        If target word is None, delete the sound at that index instead.
        """
        clone_sounds = [s for s in self._sounds]

        if target is None:
            clone_sounds.pop(begin_index)
        elif begin_index >= len(clone_sounds):
            clone_sounds = clone_sounds + target.get_sounds()
        else:
            clone_sounds = clone_sounds[:begin_index] + target.get_sounds() + clone_sounds[end_index:]

        return Word(clone_sounds)

    def index_in_word(self, target: Word, start_index: int) -> int:
        """
        Find the index of the first occurrence of target word starting from start_index in the current word.
        """
        con_len = len(target)

        for i in range(start_index, len(self)):
            if i + con_len <= len(self) and Word(self._sounds[i:i + con_len]) == target:
                return i

        return -1

    def is_appropriate(self):
        filter_words = get_filter_words_data(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data/filterwords.txt'))
        mod_curr_word = ""
        for sound in self._sounds:
            mod_curr_word += sound.get_symbol()
        for word in filter_words:
            if word in mod_curr_word:
                return False
        return True

    def is_empty(self):
        return len(self) == 0 or str(self) == ''

    def __repr__(self):
        return str(self)

    def __str__(self) -> str:
        word_str = ""

        for sound in self._sounds:
            word_str += str(sound)

        return word_str

    def __len__(self):
        return len(self._sounds)

    def __hash__(self):
        return hash(str(self))

    def __getitem__(self, item) -> Word:
        if type(item) == int:
            return Word([self._sounds[item]])
        elif type(item) == slice:
            return Word(self._sounds[item])
        else:
            raise TypeError("can only use int as index to words")

    def __eq__(self, other: Word) -> bool:
        return str(self) == str(other)

    def __ne__(self, other: Word) -> bool:
        return str(self) != str(other)


def get_filter_words_data(filename: str):
    filter_words = []

    with open(filename, encoding='utf-8') as data_file:
        lines = [l.rstrip() for l in data_file.readlines()]

        for line in lines:
            curr_temp = []
            if line.startswith("#"):
                continue
            for s in line.split(" "):
                curr_temp.append(s.split(","))

            curr_word_list = curr_temp[0]
            for i in range(1, len(curr_temp)):
                curr_word_list = list(map("".join, itertools.product(curr_word_list, curr_temp[i])))

            filter_words.extend(curr_word_list)

    return filter_words

