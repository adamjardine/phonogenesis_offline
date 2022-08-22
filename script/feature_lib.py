from __future__ import annotations

import csv
from typing import List, Tuple, Dict, Optional

from script import Sound, Word
from serializable import Serializable

REP_LEN_LIM = 3


class Particle(Serializable):
    _features: List[str]
    _is_replicated: bool

    def __init__(self, features_: List[str], is_replicated: bool) -> None:
        self._features = features_
        self._is_replicated = is_replicated

    def __len__(self):
        if self._is_replicated:
            return REP_LEN_LIM
        else:
            return 1

    def serialize(self, **kwargs):
        return str(self)

    def is_replicated(self) -> bool:
        return self._is_replicated

    def get_matching_sounds(self, phonemes: Optional[List[Word], None], feature_to_sounds: Dict[str, List[Sound]]) -> \
            List[Sound]:
        intersection = None
        full_sounds = None

        for feature in self._features:
            curr_sounds = list(dict.fromkeys(feature_to_sounds[feature.lstrip("!")]))

            if feature.startswith("!"):
                if full_sounds is None:
                    full_sounds = set(s for key in list(feature_to_sounds.keys()) if key != 'NA' for s in key)

                curr_sounds = [s for s in full_sounds if s not in curr_sounds]

            if intersection is None:
                intersection = curr_sounds
            else:
                valid = []
                for sound in intersection:
                    if sound in curr_sounds:
                        valid.append(sound)

                intersection = valid

        if phonemes is None:
            return intersection

        phoneme_sounds = [w.get_sounds()[0] for w in phonemes]

        return [s for s in intersection if s in phoneme_sounds]

    def get_features(self) -> List[str]:
        return [f for f in self._features]

    def __eq__(self, other: Particle) -> bool:
        for pt in self._features:
            if pt not in other.get_features():
                return False

        for pt in other.get_features():
            if pt not in self._features:
                return False

        return True

    def __hash__(self) -> int:
        return 0

    def __str__(self) -> str:
        return "[%s]" % ",".join(self._features)


def import_default_features() -> Tuple[
    List[str], List[Sound], Dict[str, List[str]], Dict[str, str], Dict[str, List[Sound]]]:
    import os
    return _fetch_feature_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/defaultipa.csv'))


def _fetch_feature_csv(filename: str) -> Tuple[
    List[str], List[Sound], Dict[str, List[str]], Dict[str, str], Dict[str, List[Sound]]]:
    features = []  # type: List[str]
    type_to_features = {}  # type: Dict[str, List[str]]
    feature_to_type = {}  # type: Dict[str, str]
    feature_to_sounds = {}  # type: Dict[str, List[Sound]]
    sounds = []  # type: List[Sound]

    feature_types = []

    with open(filename, encoding='utf-8') as data_file:
        lines = csv.reader(data_file)
        header_solved = False

        for line in lines:
            if len(line) == 0 or len(line[0]) == 0 or line[0] == '' or line[0] == '\ufeff':
                continue

            line = [str(s).replace('ɡ', 'g') for s in line]

            if "[TL]" in line[0]:
                if header_solved:
                    raise ImportError("Duplicate [TL] header found")

                if line.count('') > 0:
                    feature_types = line[1:line.index('', 1)]
                else:
                    feature_types = line[1:]

                for type_ in feature_types:
                    type_to_features[str(type_)] = []

                header_solved = True
                continue

            if not header_solved:
                raise ImportError("File does not start with header line begins with [TL]")

            if line.count('') > 0:
                features_ = line[1:line.index('', 1)]
            else:
                features_ = line[1:]

            if len(features_) != len(feature_types):
                raise ImportError("Feature line \'%s\' does not align with types" % str(features_))

            _sound = Sound(str(line[0]), features_)
            sounds.append(_sound)

            for i in range(0, len(features_)):
                feature_ = str(features_[i])
                type_ = feature_types[i]

                if feature_ not in feature_to_type.keys():
                    feature_to_type[feature_] = type_

                if feature_ not in features:
                    features.append(feature_)

                if feature_ not in type_to_features[type_]:
                    type_to_features[type_].append(feature_)

                if feature_ not in feature_to_sounds.keys():
                    feature_to_sounds[feature_] = []

                if _sound not in feature_to_sounds[feature_]:
                    feature_to_sounds[feature_].append(_sound)

    return features, sounds, type_to_features, feature_to_type, feature_to_sounds
