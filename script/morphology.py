import logging
import random
from abc import ABC

from script.morphology_transformer import *
from script.templates import _fetch_templates

LOGGER = logging.getLogger("app.logger")


class TransformerGenerationError(Exception):
    pass


def make_paradigm(word_templates: List[Template], rule: Rule,
                  matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                  phonemes: List[Word], feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]],
                  shuffled: bool, affix_type: Optional[str], selected_family_name: str, side: str,
                  given_gloss: Union[List[str], None], ur_words: Union[List[Word], None]):
    """
    Construct a transformer class of certain affix type based on the input "affix_type".
    """
    if affix_type == "SUFFIX":
        return SuffixParadigm(word_templates, rule, matchers, phonemes, feature_to_type, feature_to_sounds,
                              shuffled, affix_type, selected_family_name, side, given_gloss, ur_words)
    elif affix_type == "PREFIX":
        return PrefixParadigm(word_templates, rule, matchers, phonemes, feature_to_type, feature_to_sounds,
                              shuffled, affix_type, selected_family_name, side, given_gloss, ur_words)
    else:
        print("Wrong type of affix requested. By default, suffix transformer is called.")
        return SuffixParadigm(word_templates, rule, matchers, phonemes, feature_to_type, feature_to_sounds,
                              shuffled, affix_type, selected_family_name, side, given_gloss, ur_words)


class Paradigm(ABC):
    def __init__(self, word_templates: List[Template], rule: Rule,
                 matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                 phonemes: List[Word], feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]],
                 shuffled: bool, affix_type: str, selected_family_name: str, side: str,
                 given_gloss: Union[List[str], None], ur_words: Union[List[Word], None]):

        self._affix_type = affix_type
        self._selected_family_name = selected_family_name
        self._side = side
        self.rule = rule
        self.secondary = given_gloss is not None
        self.UR_words = []
        if self.secondary:
            self.UR_words = ur_words

        # A probabilistic process to decide the number of columns (either have a matching environment of the
        # chosen rule, or not have the matching environment) by counting the number of words that matches the target.
        matching_col_count, not_matching_col_count = self._get_col_count(rule, phonemes, feature_to_sounds)

        # A probabilistic process to decide the number of rows for each type (CAD, IRR, ASSIST)
        min_row = 10
        max_row = 15
        if given_gloss is None:
            self.row_count = random.randint(min_row, max_row)
        else:
            self.row_count = len(given_gloss)

        self.gen_type_dist = {"CAD": 0.4, "IRR": 0.1, "ASSIST": 0.5}

        # Select possible gloss families and among them choose one family to use.
        # Also, generate a gloss list that corresponds to the selected family name.
        if given_gloss is None:
            transform_data, glosses = self._select_glosses()
        else:
            transform_data = self._select_glosses()[0]
            glosses = given_gloss

        # Generate gloss column, column names, and template column
        self._gen_gloss_columns(glosses, transform_data, feature_to_sounds)

        # Generate word roots based on the length of the matchers (2 or 3)
        self._col_data = []
        words = []
        if not self.secondary:
            matchers = self._gen_UR(matchers, word_templates, phonemes, feature_to_type, feature_to_sounds,
                                    matching_col_count, not_matching_col_count, rule, words, self._affix_type)
        else:
            words = self.UR_words
        self._gen_affix(matchers, phonemes, feature_to_sounds,
                        matching_col_count, not_matching_col_count, rule, self._affix_type)
        print("words transfered:")
        print(words)
        self._ur_trans_operations(words, phonemes, feature_to_type, rule, feature_to_sounds, shuffled)

    def _get_col_count(self, rule: Rule, phonemes: List[Word],
                       feature_to_sounds: Dict[str, List[Sound]]) -> Tuple[int, int]:
        """
        NOTE: independent of affix type
        Get the number of all columns by counting the number of words that matches the target.
        Then, generate a gloss list that corresponds to the selected family name.
        """
        a_matcher_size = len(rule.get_a_matcher(phonemes, None, feature_to_sounds))
        matching_col_count = a_matcher_size // 4
        if a_matcher_size / 4 - matching_col_count > 0:
            matching_col_count += 1
        matching_col_count = min(3, matching_col_count)
        if self.secondary:
            self.col_count = max(min(abs(round(random.gauss(2.5, 1))), 3), matching_col_count)
            # self.col_count = random.randint(matching_col_count, min(2, matching_col_count))
        else:
            self.col_count = max(min(abs(round(random.gauss(2.5, 2))), 5), matching_col_count)
            # self.col_count = random.randint(matching_col_count + 1, 5)
        not_matching_col_count = 0
        while self.col_count - matching_col_count - not_matching_col_count > 0:
            if not_matching_col_count == 0 or random.random() < 0.75:
                not_matching_col_count += 1
            else:
                matching_col_count += 1
        return matching_col_count, not_matching_col_count

    def _select_glosses(self):
        """
        NOTE: independent of affix type
        Select possible gloss families with corresponding glosses, and among them choose one family to be used.
        """
        import os
        transform_data = _get_trans_data(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/paradigmtransdata.txt'))
        gloss_families = [gf for gf in import_default_gloss()[0] if
                          gf.get_name() == self._selected_family_name]

        glosses = []
        for gloss_family in gloss_families:
            for gloss_group in gloss_family.get_members():
                glosses.extend(gloss_group.get_glosses())

        return transform_data, glosses

    def _gen_gloss_columns(self, glosses, transform_data, feature_to_sounds):
        """
        NOTE: independent of affix type
        Generate gloss column, column names, and template column
        """
        import os
        if self.secondary:
            self.gloss_column = glosses
        else:
            self.gloss_column = random.sample(glosses, self.row_count)

        self.col_names = transform_data[self._selected_family_name][self._side][self.col_count]
        self.col_templates = _fetch_templates(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/paradigmtranstemplates.txt'),
            list(feature_to_sounds.keys()))
        random.shuffle(self.col_templates)

    def _check_valid_UR(self, word, phonemes, feature_to_type, feature_to_sounds):
        rule_applied = self.rule.apply(word, phonemes, feature_to_type, feature_to_sounds)[0]
        return word.__eq__(rule_applied)

    def _gen_words(self, size: int, gen_type_dist: Dict[str, float], word_templates: List[Template],
                   matcher: List[Word],
                   phonemes: List[Word], feature_to_type, feature_to_sounds: Dict[str, List[Sound]]):
        raise NotImplementedError

    def _gen_UR(self,
                matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                word_templates, phonemes, feature_to_type, feature_to_sounds,
                matching_col_count, not_matching_col_count, rule, words, affix_type):
        """
        NOTE: dependent of affix type
        Generate word roots based on the length of the matchers (2 or 3)
        """
        raise NotImplementedError

    def _gen_affix(self, matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                   phonemes, feature_to_sounds, matching_col_count, not_matching_col_count, rule, affix_type):
        """
        NOTE: dependent of affix type
        Generate word affixes based on the length of the matchers (2 or 3)
        """
        raise NotImplementedError

    def _ur_trans_operations(self, words, phonemes, feature_to_type, rule, feature_to_sounds, shuffled: bool):
        """
        NOTE: independent of affix type
        Generate URs and finalized data to complete the question generation process.
        """
        if not self.secondary:
            if shuffled:
                random.shuffle(words)
        if not self.secondary:
            self.UR_words = words
            self.row_count = len(self.UR_words)
        self._trans_UR_words = []
        self.UR_trans_pattern = []
        self.trans_names = []
        self.applied_core_data = []
        self._transformers = []

        for col_data in self._col_data:
            self.trans_names.append(col_data[0])
            self._transformers.append(col_data[1])
            self.UR_trans_pattern.append(str(col_data[1]))

        for word in self.UR_words:
            applied_row_list = []
            trans_row_list = []

            for col_i in range(len(self._transformers)):
                transformer = self._transformers[col_i]
                transformed_word = transformer.transform(word)
                trans_row_list.append(transformed_word)
                apply_data = rule.apply(transformed_word, phonemes, feature_to_type, feature_to_sounds)
                applied_row_list.append(apply_data[0])

            self.applied_core_data.append(applied_row_list)
            self._trans_UR_words.append(trans_row_list)

        # print("applied core data:")
        # print(self.applied_core_data)
        # print("trans UR words:")
        # print(self._trans_UR_words)

    def get_ur_words(self) -> List[Word]:
        return self.UR_words

    def get_col_data(self) -> List[Tuple[str, Transformer]]:
        return self._col_data

    def valid_row_indexes(self) -> List[int]:
        num_rows = len(self.applied_core_data)
        num_cols = len(self.applied_core_data[0])
        row_check = {}
        for r_i in range(num_rows):
            row_check[r_i] = []
        col_check = [0 for _ in range(num_cols)]

        for r_index in range(num_rows):
            for c_index in range(num_cols):
                if self._trans_UR_words[r_index][c_index] != self.applied_core_data[r_index][c_index]:
                    row_check[r_index].append(c_index)
                    col_check[c_index] += 1

        for c_i in range(num_cols):
            if c_i >= num_rows:
                for r_i in range(num_rows):
                    row_check[r_i].remove(c_i)

        valid_rows = []
        for r_i in row_check:
            if len(row_check[r_i]) > 0:
                valid_rows.append(r_i)
        return valid_rows

    def __str__(self) -> str:
        matrix_str = ""
        max_strlen = max(
            [len(self.applied_core_data[r][c]) for r in range(len(self.applied_core_data)) for c in
             range(len(self.applied_core_data[0]))] +
            [len(tn) for tn in self.trans_names])

        matrix_str += "%s  %s\n" % (
            _pad_str("base", max_strlen), "  ".join([_pad_str(str(w), max_strlen) for w in self.trans_names]))
        matrix_str += "%s  %s\n" % (
            _pad_str("---", max_strlen), "  ".join([_pad_str(str(w), max_strlen) for w in self.UR_trans_pattern]))

        for r in range(len(self.applied_core_data)):
            matrix_str += "%s  %s\n" % (_pad_str(str(self.UR_words[r]), max_strlen),
                                        "  ".join([_pad_str(str(w), max_strlen) for w in self.applied_core_data[r]]))

        return matrix_str


class PrefixParadigm(Paradigm):

    def __init__(self, word_templates: List[Template], rule: Rule,
                 matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                 phonemes: List[Word], feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]],
                 shuffled: bool, affix_type: str, selected_family_name: str, side: str,
                 given_gloss: Union[List[str], None], ur_words: Union[List[Word], None]):
        super().__init__(word_templates, rule, matchers, phonemes, feature_to_type,
                         feature_to_sounds, shuffled, affix_type, selected_family_name, side, given_gloss, ur_words)

    def _gen_UR(self,
                matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                word_templates, phonemes, feature_to_type, feature_to_sounds,
                matching_col_count, not_matching_col_count, rule, words, affix_type):
        """
        NOTE: dependent of affix type
        Generate word roots based on the length of the matchers (2 or 3)
        """
        if len(matchers) not in [2, 3]:
            raise NotImplementedError
        elif len(matchers) == 2:
            match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                           matchers[1], phonemes, feature_to_type, feature_to_sounds)

        else:  # when len(matchers) == 3
            if random.random() < 0.5:
                matchers = matchers[0], [Word(str(w1) + str(w2)) for w1 in matchers[1] for w2 in matchers[2]]
                match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                               matchers[1], phonemes, feature_to_type,
                                                               feature_to_sounds)
            else:
                matchers = [Word(str(w0) + str(w1)) for w0 in matchers[0] for w1 in matchers[1]], matchers[2]
                match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                               matchers[1], phonemes, feature_to_type,
                                                               feature_to_sounds)
        words.extend(match_words)
        words.extend(not_match_words)
        return matchers

    def _gen_affix(self, matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                   phonemes, feature_to_sounds, matching_col_count, not_matching_col_count, rule, affix_type):
        """
        NOTE: dependent of affix type
        Generate word affixes based on the length of the matchers (2 or 3)
        """
        mod_word = None
        matching_col_words = []
        not_matching_col_words = []

        for col_template in self.col_templates:
            matching_col_words.extend(
                col_template.generate_words_end_with(matchers[0], phonemes, 5, feature_to_sounds))
            not_matching_col_words.extend(
                col_template.generate_words_not_end_with(matchers[0], phonemes, 5, feature_to_sounds))

        col_index = 0

        if not_matching_col_count == 1 or random.random() < 0.5:
            self._col_data.append((self.col_names[0], make_transformer(affix_type, mod_word)))
            not_matching_col_count -= 1
            col_index += 1

        matching_col_words = [(word, 0) for word in matching_col_words]
        not_matching_col_words = [(word, 0) for word in not_matching_col_words]

        random.shuffle(matching_col_words)
        random.shuffle(not_matching_col_words)
        print(rule)
        for _ in range(matching_col_count):
            print("M")
            print(matching_col_words)
            mod_word = matching_col_words[0][0]
            print(mod_word)
            self._col_data.append((self.col_names[col_index], make_transformer(affix_type, mod_word)))
            matching_col_words.pop(0)
            matching_col_count -= 1
            matching_col_words = [(data[0], data[1] + calc_similarity(mod_word, data[0])) for data in
                                  matching_col_words]
            matching_col_words.sort(key=lambda x: x[1])
            col_index += 1

            if len(matching_col_words) == 0:
                break

        for _ in range(not_matching_col_count + matching_col_count):
            print("N")
            print(not_matching_col_words)
            mod_word = not_matching_col_words[0][0]
            print(mod_word)
            self._col_data.append((self.col_names[col_index], make_transformer(affix_type, mod_word)))
            not_matching_col_words.pop(0)
            not_matching_col_words = [(data[0], data[1] + calc_similarity(mod_word, data[0])) for data in
                                      not_matching_col_words]
            not_matching_col_words.sort(key=lambda x: x[1])

            col_index += 1

    def _gen_words(self, size: int, gen_type_dist: Dict[str, float], word_templates: List[Template],
                   matcher: List[Word],
                   phonemes: List[Word], feature_to_type, feature_to_sounds: Dict[str, List[Sound]]):
        cad_count = round(size * gen_type_dist["CAD"])

        # Doesnt depend on affix type.
        word_matching_edge_count = cad_count
        word_not_matching_edge_count = size - word_matching_edge_count
        matching_size_each_template = max(1, word_matching_edge_count // len(word_templates))
        not_matching_size_each_template = max(1, word_not_matching_edge_count // len(word_templates))
        valid_match_templates = []
        valid_not_match_templates = []
        match_words = []
        not_match_words = []
        print(size)
        print("match end: ", word_matching_edge_count)
        print("not match end: ", word_matching_edge_count)

        # Loop over the word templates to ensure at least 1 matching/not-matching word for each template
        for i in range(len(word_templates)):
            if len(match_words) < word_matching_edge_count:
                match_gen = word_templates[i].generate_words_start_with(matcher, phonemes,
                                                                        matching_size_each_template,
                                                                        feature_to_sounds)
                for word in match_gen:
                    if self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds):
                        match_words.append(word)
                if len(match_words) > 0:
                    valid_match_templates.append(word_templates[i])

            if len(not_match_words) < word_not_matching_edge_count:
                not_match_gen = word_templates[i].generate_words_not_start_with(matcher, phonemes,
                                                                                not_matching_size_each_template,
                                                                                feature_to_sounds)
                for word in not_match_gen:
                    if self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds):
                        not_match_words.append(word)
                if len(not_match_words) > 0:
                    if word_templates[i] != []:
                        valid_not_match_templates.append(word_templates[i])

        # If the number of generated matching words is less than designated matching word counts, randomly choose
        # from templates to generate more matching words, by the number of words that need to be generated more.
        if len(match_words) < word_matching_edge_count:
            extra_match_words = random.choice(valid_match_templates).generate_words_start_with(matcher, phonemes,
                                                                                               word_matching_edge_count - len(
                                                                                                   match_words),
                                                                                               feature_to_sounds)
            match_words.extend([word for word in extra_match_words if
                                self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds)])

        # Same as above, but this time for not-matching words.
        if len(not_match_words) < word_not_matching_edge_count:
            extra_not_match_words = random.choice(valid_not_match_templates).generate_words_not_start_with(
                matcher, phonemes, word_not_matching_edge_count - len(not_match_words), feature_to_sounds)
            not_match_words.extend([word for word in extra_not_match_words if
                                    self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds)])
        print("match words:")
        print(match_words)
        # print("not match words:")
        # print(not_match_words)
        return match_words, not_match_words


class SuffixParadigm(Paradigm):

    def __init__(self, word_templates: List[Template], rule: Rule,
                 matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                 phonemes: List[Word], feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]],
                 shuffled: bool, affix_type: str, selected_family_name: str, side: str,
                 given_gloss: Union[List[str], None], ur_words: Union[List[Word], None]):
        super().__init__(word_templates, rule, matchers, phonemes, feature_to_type,
                         feature_to_sounds, shuffled, affix_type, selected_family_name, side, given_gloss, ur_words)

    def _gen_UR(self,
                matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                word_templates, phonemes, feature_to_type, feature_to_sounds,
                matching_col_count, not_matching_col_count, rule, words, affix_type):
        """
        NOTE: dependent of affix type
        Generate word affixes based on the length of the matchers (2 or 3)
        """
        if len(matchers) not in [2, 3]:
            raise NotImplementedError

        elif len(matchers) == 2:
            match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                           matchers[0], phonemes, feature_to_type, feature_to_sounds)

        else:  # when len(matchers) == 3
            if random.random() < 0.5:
                matchers = matchers[0], [Word(str(w1) + str(w2)) for w1 in matchers[1] for w2 in matchers[2]]
                match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                               matchers[0], phonemes, feature_to_type,
                                                               feature_to_sounds)
            else:
                matchers = [Word(str(w0) + str(w1)) for w0 in matchers[0] for w1 in matchers[1]], matchers[2]
                match_words, not_match_words = self._gen_words(self.row_count, self.gen_type_dist, word_templates,
                                                               matchers[0], phonemes, feature_to_type,
                                                               feature_to_sounds)
        words.extend(match_words)
        words.extend(not_match_words)
        return matchers

    def _gen_affix(self, matchers: Union[Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]],
                   phonemes, feature_to_sounds, matching_col_count, not_matching_col_count, rule, affix_type):
        """
        NOTE: dependent of affix type
        Generate word affixes based on the length of the matchers (2 or 3)
        """
        mod_word = None
        matching_col_words = []
        not_matching_col_words = []

        for col_template in self.col_templates:
            matching_col_words.extend(
                col_template.generate_words_start_with(matchers[1], phonemes, 5, feature_to_sounds))
            not_matching_col_words.extend(
                col_template.generate_words_not_start_with(matchers[1], phonemes, 5, feature_to_sounds))

        col_index = 0

        if not_matching_col_count == 1 or random.random() < 0.5:
            self._col_data.append((self.col_names[0], make_transformer(affix_type, mod_word)))
            not_matching_col_count -= 1
            col_index += 1

        matching_col_words = [(word, 0) for word in matching_col_words]
        not_matching_col_words = [(word, 0) for word in not_matching_col_words]
        random.shuffle(matching_col_words)
        random.shuffle(not_matching_col_words)
        print(rule)
        for _ in range(matching_col_count):
            print("M")
            print(matching_col_words)
            mod_word = matching_col_words[0][0]
            print(mod_word)
            self._col_data.append((self.col_names[col_index], make_transformer(affix_type, mod_word)))
            matching_col_words.pop(0)
            matching_col_count -= 1
            matching_col_words = [(data[0], data[1] + calc_similarity(mod_word, data[0])) for data in
                                  matching_col_words]
            matching_col_words.sort(key=lambda x: x[1])
            col_index += 1

            if len(matching_col_words) == 0:
                break

        for _ in range(not_matching_col_count + matching_col_count):
            print("N")
            print(not_matching_col_words)
            mod_word = not_matching_col_words[0][0]
            print(mod_word)
            self._col_data.append((self.col_names[col_index], make_transformer(affix_type, mod_word)))
            not_matching_col_words.pop(0)
            not_matching_col_words = [(data[0], data[1] + calc_similarity(mod_word, data[0])) for data in
                                      not_matching_col_words]
            not_matching_col_words.sort(key=lambda x: x[1])

            col_index += 1

        # for _ in range(self._num_dummy):
        #     print("IR")
        #     print(dummy_col_words)
        #     mod_word = dummy_col_words[0][0]
        #     print(mod_word)
        #     self._col_data.append((self.col_names[col_index], make_transformer(self._dummy_affix, mod_word)))
        #     dummy_col_words.pop(0)
        #     self._num_dummy -= 1
        #     col_index += 1

    def _gen_words(self, size: int, gen_type_dist: Dict[str, float], word_templates: List[Template],
                   matcher: List[Word],
                   phonemes: List[Word], feature_to_type, feature_to_sounds: Dict[str, List[Sound]]):
        cad_count = round(size * gen_type_dist["CAD"])

        # Doesnt depend on affix type.
        word_matching_edge_count = cad_count
        word_not_matching_edge_count = size - word_matching_edge_count
        matching_size_each_template = max(1, word_matching_edge_count // len(word_templates))
        not_matching_size_each_template = max(1, word_not_matching_edge_count // len(word_templates))
        valid_match_templates = []
        valid_not_match_templates = []
        match_words = []
        not_match_words = []
        print(size)
        print("match end: ", word_matching_edge_count)
        print("not match end: ", word_matching_edge_count)

        # Loop over the word templates to ensure at least 1 matching/not-matching word for each template
        for i in range(len(word_templates)):
            if len(match_words) < word_matching_edge_count:
                match_gen = word_templates[i].generate_words_end_with(matcher, phonemes,
                                                                      matching_size_each_template,
                                                                      feature_to_sounds)
                for word in match_gen:
                    if self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds):
                        match_words.append(word)
                if len(match_words) > 0:
                    valid_match_templates.append(word_templates[i])

            if len(not_match_words) < word_not_matching_edge_count:
                not_match_gen = word_templates[i].generate_words_not_end_with(matcher, phonemes,
                                                                              not_matching_size_each_template,
                                                                              feature_to_sounds)
                for word in not_match_gen:
                    if self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds):
                        not_match_words.append(word)
                if len(not_match_words) > 0:
                    valid_not_match_templates.append(word_templates[i])

        # If the number of generated matching words is less than designated matching word counts, randomly choose
        # from templates to generate more matching words, by the number of words that need to be generated more.
        if len(match_words) < word_matching_edge_count:
            extra_match_words = random.choice(valid_match_templates).generate_words_end_with(
                matcher, phonemes, word_matching_edge_count - len(match_words), feature_to_sounds)
            match_words.extend([word for word in extra_match_words if
                                self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds)])

        # Same as above, but this time for not-matching words.
        if len(not_match_words) < word_not_matching_edge_count:
            extra_not_match_words = random.choice(valid_not_match_templates).generate_words_not_end_with(
                matcher, phonemes, word_not_matching_edge_count - len(not_match_words), feature_to_sounds)
            not_match_words.extend([word for word in extra_not_match_words if
                                    self._check_valid_UR(word, phonemes, feature_to_type, feature_to_sounds)])

        print("match words:")
        print(match_words)
        return match_words, not_match_words


class ParadigmGenerator:
    def __init__(self, rule: Rule, phonemes: List[Word], templates: List[Template],
                 feature_to_type: Dict[str, str], feature_to_sounds: Dict[str, List[Sound]]):
        self._phonemes = phonemes
        self._feature_to_type = feature_to_type
        self._feature_to_sounds = feature_to_sounds
        self._rule = rule
        self._templates = templates

    def _get_valid_question(self, shuffled: bool, affix_type: Optional[str]) -> [Paradigm, Paradigm]:
        retry_limit = 2
        trial = 0
        import random
        import os
        transform_data = _get_trans_data(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/paradigmtransdata.txt'))
        selected_family_name = random.choice(list(transform_data.keys()))
        sides = ["side1", "side2"]
        random.shuffle(sides)
        primary_side, secondary_side = sides[0], sides[1]
        return_paradigm = [None, None]
        while trial < retry_limit:
            try:
                matchers = construct_matchers(self._rule, self._phonemes, self._feature_to_sounds)
            except ValueError:
                return None
            paradigm1 = make_paradigm(self._templates, self._rule, matchers, self._phonemes,
                                      self._feature_to_type, self._feature_to_sounds,
                                      shuffled, affix_type,
                                      selected_family_name=selected_family_name, side=primary_side, given_gloss=None,
                                      ur_words=None)
            return_paradigm[0] = paradigm1
            given_gloss = paradigm1.gloss_column
            ur_words = paradigm1.UR_words
            p2_col_count = 0

            if (paradigm1.col_count <= 3) and (paradigm1 is not None):
                if affix_type == "PREFIX":
                    secondary_affix_type = "SUFFIX"
                else:
                    secondary_affix_type = "PREFIX"
                paradigm2 = make_paradigm(self._templates, self._rule, matchers, self._phonemes,
                                          self._feature_to_type, self._feature_to_sounds,
                                          shuffled, secondary_affix_type,
                                          selected_family_name=selected_family_name, side=secondary_side,
                                          given_gloss=given_gloss, ur_words=ur_words)
                return_paradigm[1] = paradigm2
                p2_col_count = paradigm2.col_count

            print("colcount: " + str(paradigm1.col_count) + "/" + str(p2_col_count))
            return return_paradigm

        LOGGER.error("Rule %s\n" % str(self._rule))
        LOGGER.error("Phoneme %s\n" % str(self._phonemes))
        LOGGER.error("Exceeded maximum retry limit. Failed to find a question!\n")
        return None

    def get_paradigm_question(self, shuffled: bool, isIPAg: bool, feature_to_type: Dict[str, str],
                              feature_to_sounds: Dict[str, List[Sound]], affix_type: Optional[str]) -> Optional[Dict]:
        questions = self._get_valid_question(shuffled, affix_type)

        if questions is None:
            return None

        poi = " ".join(self._rule.get_interest_phones(self._phonemes, feature_to_type, feature_to_sounds)[1])

        header_row = []
        trans_patterns = []
        ur_words = [str(w) for w in questions[0].UR_words]
        core_data = []
        for _ in range(len(questions[0].applied_core_data)):
            core_data.append([])
        rule = str(self._rule)
        phonemes = [str(w) for w in self._phonemes]
        templates = str(self._templates)
        gloss = [str(w) for w in questions[0].gloss_column]

        for question in questions:
            if question is not None:
                header_row.extend([str(w) for w in question.trans_names])
                trans_patterns.extend(str(w) for w in question.UR_trans_pattern)
                for i in range(len(question.applied_core_data)):
                    core_data[i].extend([str(w) for w in question.applied_core_data[i]])

        if isIPAg:
            question_data = {
                'header_row': [str(w).replace('g', 'ɡ') for w in header_row],
                'trans_patterns': [str(w).replace('g', 'ɡ') for w in trans_patterns],
                'ur_words': [str(w).replace('g', 'ɡ') for w in ur_words],
                'core_data': [[str(w).replace('g', 'ɡ') for w in row] for row in core_data],
                'rule': rule,
                'phonemes': [str(w).replace('g', 'ɡ') for w in phonemes],
                'templates': templates,
                'Gloss': gloss,
                'poi': poi.replace('g', 'ɡ')
            }
        else:
            question_data = {
                'header_row': header_row,
                'trans_patterns': trans_patterns,
                'ur_words': ur_words,
                'core_data': core_data,
                'rule': rule,
                'phonemes': phonemes,
                'templates': templates,
                'Gloss': gloss,
                'poi': poi
            }

        LOGGER.debug(question_data)
        return question_data


def _get_trans_data(filename: str):
    types = {}

    with open(filename, encoding='utf-8') as data_file:
        lines = [l.rstrip() for l in data_file.readlines()]
        curr_type = None
        curr_side = None

        for line in lines:
            line = line.replace('ɡ', 'g')

            if len(line) == 0:
                continue

            if line.startswith("### "):
                curr_type = line.lstrip("### ")
                continue

            if line.startswith("## "):
                curr_side = line.lstrip("## ")
                continue

            if not curr_type:
                raise ValueError('Must have a line starts with "### " to define gloss family type.')

            if curr_type not in types:
                types[curr_type] = {"side1": {}, "side2": {}}

            trans_types = line.split(',')
            target_size = int(trans_types[0])

            assert len(trans_types) == target_size + 1

            types[curr_type][curr_side][target_size] = trans_types[1:]

    return types


def construct_matchers(rule: Rule, phonemes: Optional[List[Word]], feature_to_sounds: Dict[str, List[Sound]]) -> Union[
    Tuple[List[Word], List[Word]], Tuple[List[Word], List[Word], List[Word]]]:
    # can not have edges
    c_matchers = rule.get_c_matchers(phonemes, feature_to_sounds)
    d_matchers = rule.get_d_matchers(phonemes, feature_to_sounds)
    cd_index = random.randint(0, len(c_matchers) - 1)
    c_matcher = c_matchers[cd_index]
    d_matcher = d_matchers[cd_index]
    a_matcher = rule.get_a_matcher(phonemes, None, feature_to_sounds)

    if len(c_matcher) == 0 and len(d_matcher) == 0:
        raise ValueError("Impossible to have both cmatcher and dmatcher to be empty")

    if len(c_matcher) == 0:
        return a_matcher, d_matcher

    if len(d_matcher) == 0:
        return c_matcher, a_matcher

    return c_matcher, a_matcher, d_matcher


def _pad_str(org_str: str, padding_size: int) -> str:
    while len(org_str) < padding_size:
        org_str += " "

    return org_str


def calc_similarity(word1: Word, word2: Word) -> int:
    index = 0
    similarity = 0
    while index < len(word1) and index < len(word2):
        if word1[index] == word2[index]:
            similarity += 1

        index += 1
    return similarity
