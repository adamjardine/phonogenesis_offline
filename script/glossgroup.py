from __future__ import annotations

import random
from typing import List, Tuple

from serializable import Serializable


class GlossGroup(Serializable):
    _glosses: List[str]
    _family: GlossFamily

    def __init__(self, glosses: List[str], family=None) -> None:
        self._glosses = glosses
        self._family = family

        if self._family:
            family.add_member(self)

    def get_family(self) -> GlossFamily:
        return self._family

    def get_glosses(self) -> List[str]:
        return self._glosses

    def serialize(self, **kwargs):
        return str(self)

    def pick(self) -> str:
        return random.choice(self._glosses)

    def __str__(self):
        return "GROUP %s - %s" % (str(self._family), str(self._glosses))


class GlossFamily(Serializable):
    _name: str
    _members: List[GlossGroup]

    def __init__(self, name: str) -> None:
        self._name = name
        self._members = []

    def add_member(self, member: GlossGroup) -> bool:
        if member not in self._members:
            self._members.append(member)
            return True

        return False

    def get_name(self) -> str:
        return self._name

    def get_members(self) -> List[GlossGroup]:
        return self._members

    def serialize(self, **kwargs):
        return str(self)

    def __str__(self):
        return self._name


def import_default_gloss() -> Tuple[List[GlossFamily], List[GlossGroup]]:
    import os
    return _fetch_gloss(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/defaultgloss.txt'))


def _fetch_gloss(filename: str) -> Tuple[List[GlossFamily], List[GlossGroup]]:
    gloss_groups = []
    gloss_families = []
    current_family = None

    with open(filename, encoding='utf-8') as data_file:
        lines = [l.rstrip('\n') for l in data_file.readlines()]

        for line in lines:
            line = line.replace('ɡ', 'g')

            if len(line) == 0:
                continue

            if line.startswith("### "):
                current_family = GlossFamily(line.lstrip("### "))
                gloss_families.append(current_family)
                continue

            if current_family is None:
                raise ValueError("Family not found")

            data = line.split(" | ")

            gloss_groups.append(GlossGroup(data, current_family))

    return gloss_families, gloss_groups
