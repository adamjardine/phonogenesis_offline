from __future__ import annotations

import random
from typing import List, Dict, Optional, Tuple

from script import Word, Particle, Sound
from serializable import Serializable


class Template(Serializable):
    _size: int
    _components: List[Particle]

    def __init__(self, components: List[Particle]) -> None:
        self._components = components
        self._size = len(components)

    def __len__(self):
        size = 0
        for comp in self._components:
            size += len(comp)

        return size

    def __reversed__(self):
        return Template(self._components[::-1])

    def serialize(self, **kwargs):
        return str(self)

    def is_replicated(self) -> bool:
        return True in [c.is_replicated() for c in self._components]

    def is_d_match(self, word: Word, index: int, d_edge: bool, feature_to_sounds: Dict[str, List[Sound]],
                   phonemes: Optional[None, List[Word]]) -> Tuple[bool, int]:
        if index + len(self) <= len(word) - 1:
            if d_edge and index + len(self) < len(word) - 1:
                return False, 0

            sector = word[index + 1:]
        else:
            sector = word[index + 1:index + len(self)]

        match_data = self._recur_match(0, sector, 0, feature_to_sounds, phonemes)

        if not match_data[1] and d_edge:
            return False, 0
        else:
            return match_data[0], 0

    def _recur_match(self, sec_index: int, sec: Word, part_index: int, feature_to_sounds: Dict[str, List[Sound]],
                     phonemes: Optional[None, List[Word]]) -> Tuple[bool, bool]:
        if sec_index >= len(sec) and sec_index >= len(self._components):
            return True, True

        if part_index >= len(self._components):
            return True, False

        if sec_index >= len(sec):
            return False, False

        target_word = sec[sec_index]
        if len(target_word) != 1:
            raise ValueError("Should be matching length 1 str")
        target = target_word.get_sounds()[0]

        curr_part = self._components[part_index]
        matching_sounds = curr_part.get_matching_sounds(phonemes, feature_to_sounds)

        if target not in matching_sounds:
            return False, False

        if curr_part.is_replicated():
            rep2 = False
            rep3 = False

            if sec_index + 1 < len(sec):
                target2 = sec[sec_index + 1].get_sounds()[0]

                if target2 in matching_sounds:
                    rep2 = True

            if rep2 and sec_index + 2 < len(sec):
                target3 = sec[sec_index + 2].get_sounds()[0]

                if target3 in matching_sounds:
                    rep3 = True

            if rep3:
                data3 = self._recur_match(sec_index + 3, sec, part_index + 1, feature_to_sounds, phonemes)
                if data3[0]:
                    return data3

            if rep2:
                data2 = self._recur_match(sec_index + 2, sec, part_index + 1, feature_to_sounds, phonemes)
                if data2[0]:
                    return data2

        return self._recur_match(sec_index + 1, sec, part_index + 1, feature_to_sounds, phonemes)

    def generate_words_end_with(self, end_word_list: List[Word], phonemes: List[Word],
                                size_limit: int, feature_to_sounds: Dict[str, List[Sound]]):
        end_word_sound_list = end_word_list[0].get_sounds()
        end_size = len(end_word_sound_list)
        template_end_particles = self._components[len(self._components) - end_size:]

        for i in range(end_size):
            if end_word_sound_list[i] not in template_end_particles[i].get_matching_sounds(phonemes, feature_to_sounds):
                return []

        clipped_template = Template(self._components[:len(self._components) - end_size])
        clipped_words = clipped_template.generate_word_list(phonemes, size_limit, feature_to_sounds)

        return [Word(str(w) + str(random.choice(end_word_list))) for w in clipped_words]

    def generate_words_not_end_with(self, avoid_words: List[Word], phonemes: List[Word], size_limit: int,
                                    feature_to_sounds: Dict[str, List[Sound]]):
        result = []
        regen_limit = 10

        while regen_limit > 0:
            words = self.generate_word_list(phonemes, size_limit * 10, feature_to_sounds)
            for word in words:
                if True not in [str(word).endswith(str(avoid)) for avoid in avoid_words]:
                    result.append(word)

                if len(result) >= size_limit:
                    return result

            regen_limit -= 1

        return []

    def generate_words_start_with(self, start_word_list: List[Word], phonemes: Optional[List[Word], None],
                                  size_limit: Optional[int, None],
                                  feature_to_sounds: Dict[str, List[Sound]]):
        start_word_sound_list = start_word_list[0].get_sounds()
        start_size = len(start_word_sound_list)
        template_start_particles = self._components[:start_size]

        for i in range(start_size):
            if start_word_sound_list[i] not in template_start_particles[i].get_matching_sounds(phonemes,
                                                                                               feature_to_sounds):
                return []

        # if len(self._components) == 1:
        #     return start_word_list

        clipped_template = Template(self._components[start_size:])
        clipped_words = clipped_template.generate_word_list(phonemes, size_limit, feature_to_sounds)

        return [Word(str(random.choice(start_word_list)) + str(w)) for w in clipped_words]

    def generate_words_not_start_with(self, avoid_words: List[Word], phonemes: List[Word], size_limit: int,
                                      feature_to_sounds: Dict[str, List[Sound]]):
        result = []
        regen_limit = 10

        while regen_limit > 0:
            words = self.generate_word_list(phonemes, size_limit * 10, feature_to_sounds)
            for word in words:
                if True not in [str(word).startswith(str(avoid)) for avoid in avoid_words]:
                    result.append(word)

                if len(result) >= size_limit:
                    return result

            regen_limit -= 1

        return []

    def generate_word_list(self, phonemes: Optional[List[Word], None], size_limit: Optional[int, None],
                           feature_to_sounds: Dict[str, List[Sound]], **kwargs) -> \
            List[Word]:
        """
        Generate a word list with current template using given environments.

        If target_phones is None, then words are constructed using given full phoneme, otherwise only words with
        sound(s) from target_phones will be selected. When generating words with phones of interest, each sound in the
        interested phones will be given equivalent chance to be selected (i.e. attempt to achieve even distribution
        among interested phones)

        If size_limit is None, then all words matching current template will be recorded & returned, otherwise up to
        size_limit words will be returned.

        If size_limit is None, then target_phone MUST be None too (i.e. to generate with phones of interest, a size
        limit must be defined).
        """
        primary_interest = kwargs.get('primary_interest', None)
        secondary_interest = kwargs.get('secondary_interest', None)

        if size_limit is None:
            if primary_interest is not None:
                raise AttributeError("Not allowed to have target phoneme when not having a size limit")

        word_len = len(self._components)

        part_sounds = []
        interest_sounds = []
        interest_indexes = []
        secondary_interest_sounds = []
        secondary_interest_indexes = []

        word_list = set([])

        if word_len == 0:
            return []

        for particle in self._components:
            part_sound = particle.get_matching_sounds(phonemes, feature_to_sounds)
            part_sounds.append(part_sound)

            if primary_interest is not None:
                interest_sound = [s for s in part_sound if Word([s]) in primary_interest]

                if interest_sound != [] and len(interest_sound) > 0:
                    interest_indexes.append(len(interest_sounds))

                interest_sounds.append(interest_sound)

            if secondary_interest is not None:
                secondary_interest_sound = [s for s in part_sound if Word([s]) in secondary_interest]

                if secondary_interest_sound != [] and len(secondary_interest_sound) > 0:
                    secondary_interest_indexes.append(len(secondary_interest_sounds))

                secondary_interest_sounds.append(secondary_interest_sound)

        interest_total = len(interest_indexes)

        if size_limit is None:
            result = self._recur_full_word_list(part_sounds, 0, [''])
            return [Word(r) for r in result]
        else:
            word_count = 0
            if primary_interest is None:
                while word_count < size_limit:
                    curr_word = []  # type: List[Sound]

                    for i in range(word_len):
                        if part_sounds[i] == [] or len(part_sounds[i]) == 0:
                            return []
                        curr_word.append(random.choice(part_sounds[i]))

                    word_list.add(Word(curr_word))
                    word_count += 1
            else:
                if interest_total == 0:
                    return []

                while word_count < size_limit:
                    interest_past = 0
                    interest_added = 0
                    possibility = 1.0 / interest_total

                    curr_word = [Sound('', []) for _ in range(0, word_len)]  # type: List[Sound]
                    unordered_index = [i for i in range(0, word_len)]
                    random.shuffle(unordered_index)

                    for i in unordered_index:
                        if interest_added < 3 and i in interest_indexes:
                            if random.random() < possibility or interest_added + interest_total - interest_past <= 1:
                                curr_word[i] = random.choice(interest_sounds[i])
                                interest_added += 1
                            else:
                                curr_word[i] = random.choice(part_sounds[i])

                            interest_past += 1
                        elif random.random() < 0.33 and i in secondary_interest_indexes:
                            curr_word[i] = random.choice(secondary_interest_sounds[i])
                        else:
                            curr_word[i] = random.choice(part_sounds[i])

                    word_list.add(Word(curr_word))
                    word_count += 1

            result = list(word_list)
            return result

    def _recur_full_word_list(self, comb_sound: List[List[Sound]], index: int, words: List[str]) -> List[str]:
        if index >= len(comb_sound):
            return words
        else:
            new_words = []  # type: List[str]

            for sound in comb_sound[index]:
                for word in words:
                    new_words.append(word + str(sound))

            return self._recur_full_word_list(comb_sound, index + 1, new_words)

    def get_components(self) -> List[Particle]:
        """
        Returns the particles current template contains
        """
        return [block for block in self._components]

    def __str__(self) -> str:
        return "-".join([str(p) for p in self._components])


def import_default_templates(feature_pool: List[str]) -> List[Template]:
    import os
    return _fetch_templates(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/defaulttemplate.txt"),
                            feature_pool)


def parse_template_line(line: str, feature_pool: List[str]) -> Template:
    """
    Line should be in format of [Particle Data]-[Particle Data]-...
    e.g. [consonant]-[vowel]-[obstruent,voiceless]-[obstruent,voiceless]-[vowel]

    All letter 'g' is converted to conventional g (ipa g will be replaced)
    """
    line = line.replace('ɡ', 'g')
    particle_list = line.split("-")
    particles = []

    for particle_data in particle_list:
        particle_data = particle_data.rstrip('\r').rstrip('\n').rstrip(']').lstrip('[')

        is_replicated = False
        if particle_data[0] == '*':
            is_replicated = True
            particle_data = particle_data[1:]

        feature_list = particle_data.split(",")
        for feature in feature_list:
            if feature not in feature_pool:
                raise ImportError("Template line %s does not conform to the given features." % line)

        particles.append(Particle(feature_list, is_replicated))

    return Template(particles)


def _fetch_templates(filename: str, feature_pool: List[str]) -> List[Template]:
    """
    Fetch templates from the given file, assuming each line of the file conforms to template line format.
    Default encoding utf-8

    Feature pool needed for validity check during parsing
    """
    templates = []  # type: List[Template]

    with open(filename, encoding='utf-8') as data_file:
        lines = [line.rstrip('\n') for line in data_file.readlines()]

        for line in lines:
            templates.append(parse_template_line(line, feature_pool))

    return templates
