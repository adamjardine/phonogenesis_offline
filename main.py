import sys
import os
# sys.path.insert(0, os.path.abspath("..")) # Added to get Python3 to look at folder for script package
import random
import re

from script import *
from questions import *
from tipadic import *

def tipafy(s):
    """For writing LaTeX output with tipa package. Rewrite string s of IPA symbols as string of tipa values"""

    s = re.sub(r"(.)"+"͡"+"(.)",r"\\t{\1\2}",s)
    s = re.sub(r"(.)"+"̥",r"\\r*\1",s)

    r = ""
    for a in s:
        try:
            r+=TIPA_DIC[a]
        except KeyError:
            print("Warning: '"+a+"' not found in dictionary")
            r+=a
    return "\\textipa{"+r+"}"


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
    plainlines = []
    latexlines = ["\\begin{tabular}[t]{"+"l"*(len(questn["header_row"])+1)+"}"]

    line = ""
    lline = ""

    hdr = questn["header_row"]
    for i in hdr:
        line+=i+"\t\t"
        lline+=i+"\t&\t"

    plainlines.append(line+"gloss")
    latexlines.append(lline+"gloss \\")

    row = 0
    for l in questn["core_data"]:
        line = ""
        lline = ""
        for i in l:
            line+=i+"\t\t"
            lline+=tipafy(i)+"\t&\t"
        plainlines.append(line+questn["gloss"][row])
        latexlines.append(lline+"``"+questn["gloss"][row]+"''\t\\\\")
        # print(line+questn["gloss"][row])
        row+=1

    plainlines.append("")
    latexlines.append("\\end{tabular}")
    latexlines.append("")
    # print()

    plainlines.append("Answer:")
    latexlines.append("Answer:")
    # print("Answer:")

    plainlines.append("Rule: "+questn["rule_content"])
    latexlines.append("Rule: "+questn["rule_content"])
    # print("Rule: "+questn["rule_content"])

    plainlines.append("Underlying forms: ")
    latexlines.append("Underlying forms: ")

    latexlines.append("\\begin{tabular}{ll}")

    plainlines.append("UR\t\tgloss")
    latexlines.append("UR\t&\tgloss")

    for i in range(0,len(questn["UR"])):
        plainlines.append("/"+questn["UR"][i]+'/\t"'+questn["gloss"][i]+'"')
        latexlines.append("/"+tipafy(questn["UR"][i])+"/\t&\t``"+questn["gloss"][i]+"''\t\\\\")
        # print("/"+questn["UR"][i]+'/\t"'+questn["gloss"][i]+'"')

    for i in range(0,len(questn["trans_patterns"])):
        plainlines.append("/"+questn["trans_patterns"][i]+'/\t"'+questn["header_row"][i]+'"')
        latexlines.append("/"+tipafy(questn["trans_patterns"][i])+'/\t&\t``'+questn["header_row"][i]+"''\t\\\\")
        # print("/"+questn["trans_patterns"][i]+'/\t"'+questn["header_row"][i]+'"')

    latexlines.append("\\end{tabular}")

    for i in plainlines:
        print(i)

    print()
    print("LaTeX:\n")
    for i in latexlines:
        print(i)

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

