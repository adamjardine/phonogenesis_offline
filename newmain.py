import sys
import os
# sys.path.insert(0, os.path.abspath("..")) # Added to get Python3 to look at folder for script package
import random

from script import *

if __name__ == '__main__':

    DEFAULT_DATA = get_default_data() # from ../app/__init__.py

    # HERE: the following is from ../app/routes.py in the create_quiz() function. Getting this to work probably gets the whole thing to work.
    # size = int(question_attr['size'])
    # max_cadt = int(question_attr['maxCADT'])
    size = 2
    max_cadt= 4
    # rule = DEFAULT_DATA['rules'][question_attr['rule']] # DEFAULT_DATA['rules'] is a dict from string names of rules to rule objects
    rule = DEFAULT_DATA['rules'][random.choice(list(DEFAULT_DATA['rules']))] 
    phonemes = DEFAULT_DATA['phonemes']
    gen = Generator(phonemes, DEFAULT_DATA['templates'], rule, 5, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    q_data = gen.generate(GenMode.IPAg, [size, max_cadt * 5], True, False,
                              DEFAULT_DATA['gloss_grp'])

    # print(q_data)

    print ("UR\tSR\tGloss")
    for i in range(1,len(q_data['UR'])):
        s = q_data['UR'][i]+"\t"
        s += q_data['SR'][i]+"\t"
        s += q_data['Gloss'][i]+"\t"
        print(s)
    print(q_data['rule'])

