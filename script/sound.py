from __future__ import annotations

from typing import List, Dict, Any, Optional

from serializable import Serializable

_SYMBOL = {}  # type: Dict[str, Sound]
id_num = 1  # type: int


class Sound(Serializable):
    _num: int
    _features: List[str]
    _symbol: str

    def __init__(self, symbol: str, features: List[str]) -> None:
        global id_num

        if symbol == '' or len(symbol) == 0:
            self._num = -1
        else:
            self._num = id_num
            id_num += 1

        self._features = features
        self._symbol = symbol

        if symbol in _SYMBOL.keys():
            raise ValueError("Duplicated symbol %s not allowed!" % symbol)

        if self._num >= 1 and symbol != '':
            _SYMBOL[symbol] = self

    def serialize(self, **kwargs):
        return str(self)

    def get_features(self) -> List[str]:
        return [f for f in self._features]

    def get_symbol(self) -> str:
        return self._symbol

    def get_transformed_sound(self, target_particle: Any, ignored_types: List[str], feature_to_type: Dict[str, str],
                              feature_to_sounds: Dict[str, List[Sound]]) -> Optional[Sound, None]:
        """
        Transform current sound to conform to the given particle with given environments.
        Current sound is compared to all sounds matching target particle.

        Ignored types defines feature types that are not to be evaluated while transforming.

        There are two types of matching: loose match and tight match.
        Tight match require strict equivalence (including feature NA), while loose match validates if either feature is
        NA.

        The function returns the one and only one strict match found. If no strict match is founded, it returns the one
        and only one loose match found.
        If there are more than one strict matches, or there are more than one loose matches when there is no strict
        match, an error is raised indicating the transformation is ambiguous.
        """
        from script.feature_lib import Particle

        if not isinstance(target_particle, Particle):
            raise AttributeError("target particle must be a Particle")

        specified_types = [feature_to_type[f] for f in target_particle.get_features()]

        loose_match = []  # type: List[Sound]
        tight_match = []  # type: List[Sound]

        for sound in target_particle.get_matching_sounds(None, feature_to_sounds):
            target_features = sound.get_features()
            passed = True
            is_loose = False

            for i in range(0, len(self._features)):
                target_feature = target_features[i]
                this_feature = self._features[i]

                if target_feature == 'NA':
                    target_type = feature_to_type[this_feature]
                else:
                    target_type = feature_to_type[target_feature]

                if target_type not in specified_types and target_type not in ignored_types:
                    if target_feature != this_feature:
                        if target_feature == 'NA' or this_feature == 'NA':
                            is_loose = True
                        else:
                            passed = False
                            break

            if passed:
                if is_loose:
                    loose_match.append(sound)
                else:
                    tight_match.append(sound)

        if len(loose_match) == 0 and len(tight_match) == 0:
            return None

        if len(tight_match) > 1:
            raise ValueError("multiple tight matches!! %s" % [str(s) for s in tight_match])

        if len(tight_match) == 1:
            return tight_match[0]

        if len(loose_match) > 1:
            raise ValueError("multiple loose matches found %s" % [str(s) for s in loose_match])

        if len(loose_match) == 1:
            return loose_match[0]

        raise EOFError("cant reach this line")

    def get_num(self) -> int:
        return self._num

    def __hash__(self) -> int:
        return self._num

    def __getitem__(self, item: str) -> Sound:
        return _SYMBOL[item]

    def __str__(self) -> str:
        return self._symbol

    def __eq__(self, other: Sound) -> bool:
        return self._num == other.get_num()

    def __ne__(self, other: Sound) -> bool:
        return self._num != other.get_num()

    def __lt__(self, other: Sound) -> bool:
        return self._num < other.get_num()

    def __le__(self, other: Sound) -> bool:
        return self._num <= other.get_num()

    def __gt__(self, other: Sound) -> bool:
        return self._num > other.get_num()

    def __ge__(self, other: Sound) -> bool:
        return self._num >= other.get_num()
