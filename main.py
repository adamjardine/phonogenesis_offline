import sys
import os
# sys.path.insert(0, os.path.abspath("..")) # Added to get Python3 to look at folder for script package
import random

from script import *
from questions import *


if __name__ == '__main__':

    settings = {
        "shuffle" : True,
        "isIPAg"  : False,
        "rule_family" : "Random"
    }

    DEFAULT_DATA = get_default_data() # from ../app/__init__.py

    print("initializing...")
    questn = get_morphology_question(settings,DEFAULT_DATA)

    print("Problem set generated. Problem set:")
    line = ""

    hdr = questn["header_row"]
    for i in hdr:
        line+=i+"\t\t"
    print(line+"gloss")

    row = 0
    for l in questn["core_data"]:
        line = ""
        for i in l:
            line+=i+"\t\t"
        print(line+questn["gloss"][row])
        row+=1

    print("Answer:")
    print(questn["rule_content"])

    # print(hdr)
    # print(questn["core_data"])
    # print(questn["gloss"])

    # size = 2
    # max_cadt= 4
    # # rule = DEFAULT_DATA['rules'][question_attr['rule']] # DEFAULT_DATA['rules'] is a dict from string names of rules to rule objects
    # rule = DEFAULT_DATA['rules'][random.choice(list(DEFAULT_DATA['rules']))] 
    # phonemes = DEFAULT_DATA['phonemes']
    # gen = Generator(phonemes, DEFAULT_DATA['templates'], rule, 5, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    # rule_type = rule.get_rule_type(phonemes, DEFAULT_DATA['f2t'], DEFAULT_DATA['f2ss'])
    # q_data = gen.generate(GenMode.IPAg, [size, max_cadt * 5], True, False,
    #                           DEFAULT_DATA['gloss_grp'])

    # print(q_data)

    # print ("UR\tSR\tGloss")
    # for i in range(1,len(q_data['UR'])):
    #     s = q_data['UR'][i]+"\t"
    #     s += q_data['SR'][i]+"\t"
    #     s += q_data['Gloss'][i]+"\t"
    #     print(s)
    # print(q_data['rule'])

