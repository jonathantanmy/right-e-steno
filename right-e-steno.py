# Copyright 2021 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import collections
import re

LONGEST_KEY = 10

Node = collections.namedtuple('Node', 'word conts')
def make_node():
    return Node([], collections.defaultdict(make_node))
root = make_node()

def process_line(line):
    if not re.match('[a-z]+$', line):
        return
    current_node = root
    remain = line
    while remain:
        match = re.match('[^aeiouwy]*', remain)
        current_node = current_node.conts[match.group()]
        remain = remain[match.end():]
        if not remain:
            break
        match = re.match('[aeiouwy]+', remain)
        current_node = current_node.conts[match.group()]
        remain = remain[match.end():]
    if not current_node.word:
        current_node.word.append(line)

with open('/usr/share/dict/words') as f:
    for rawline in f:
        process_line(rawline.strip())

def resolve(node, accum):
    nodes = []
    for text, n in node.conts.items():
        if re.match(accum + '$', text):
            nodes.append(n)
    return nodes

State = collections.namedtuple('State', 'node accum is_accum_vowel')

def resolve_and_accum(states, accum_str):
    is_accum_vowel = not re.search('[aeiouwy]', accum_str)
    new_states = []
    for s in states:
        nodes = []
        accum = s.accum
        if s.is_accum_vowel == is_accum_vowel:
            nodes.extend(resolve(s.node, s.accum))
            accum = accum_str
        else:
            nodes.append(s.node)
            accum += accum_str
        for n in nodes:
            new_states.append(State(n, accum, not is_accum_vowel))
    return new_states

def check_word(states):
    for s in states:
        resolved = [n for n in resolve(s.node, s.accum) if n.word]
        if resolved:
            return resolved[0].word[0]
    return None

def dictify(s, steno_order, d, basic_d):
    for term in s.split():
        if term.startswith('#'):
            continue
        if '-' in term:
            word_part, chord_part = term.split('-')
            if chord_part in d:
                raise ValueError(f'{word_part}: already have {chord_part} ({d})')
            if '|' in word_part:
                d[chord_part] = '(?:' + word_part + ')'
                basic_d[chord_part] = word_part.split('|')[0]
            else:
                d[chord_part] = word_part
                basic_d[chord_part] = word_part
            continue
        current_term = term
        current_chord = ''
        while current_term:
            matches = ((re.match(w, current_term), c) for c, w in d.items())
            candidates = sorted(((m.end(), c) for m, c in matches if m),
                    reverse=True)
            if not candidates:
                raise ValueError(f'cannot find chord for "{term}"')
            match_length, c = candidates[0]
            current_term = current_term[match_length:]
            current_chord += c
        if current_chord in d:
            raise ValueError(f'{term}: already have {current_chord} ({d})')
        d[current_chord] = term
        basic_d[current_chord] = term
    for c, w in d.items():
        if (''.join(sorted(c, key=lambda x: steno_order.index(x))) != c):
            raise ValueError(f'"{w}" "{c}" violates steno order')
left_to_re = {}
left_to_basic = {}
dictify('''
s-S t-T k-K p-P w-W
h-H r-R d-TK b-PW l-HR
f-TP m-PH n-TPH y-KWR g-TKPW
c-KP j-SKWR q-KW v-STP x-SPW
z-STKPW th wh sh st
fr pr dr tr ch
kn-TKPH br gr thr cr
sp tw sm pl bl
sl str fl cl gl
ph-TKP phr sw spr sc
wr sq sn sk gh
dw sch spl
''', 'STKPWHR', left_to_re, left_to_basic)
middle_to_re = {}
middle_to_basic = {}
dictify('''
a-A e-E i|y-EU o-O u-U
ee|iu|ui|iw|wi|yu|uy|yw|wy-AOU ei|ie|ey|ye-AOE oa|ao-AO oe|eo-OE
eu|ue|ew|we-AOEU ai|ia|ay|ya-AEU io|oi|yo|oy-OEU
oo|au|ua|aw|wa-AU ou|uo|ow|wo-OU ea|ae-AE
''', 'AOEU', middle_to_re, middle_to_basic)
right_to_re = {}
right_to_basic = {}
dictify('''
h|gh-F
r|rr-R p|pp-P b|bb-B l|ll-L g|gg-G t-T s-S d|dd-D z|zz-Z
n|nn-PB m|mm-PL f|ff-PG v-BG c|cc-LG x-RLG
nd rd ld rld
ss-BS ls ns ps rps rs
k-GS nk rk|lk-RGS ck|q-LGS sk-BGS  
st-BT ght-GT rt|bt-RT tt-RPT rst|nst-RBT nt ct ft xt lt pt mpt-PBLT
nx-RPBLG
sh-BLG lsh|rsh-RBLG
ch-PLG lch|rch-RPLG  
nc|nch|nsh-PBLG
ng rg
lf|rf-RPG
lv|rv-RBG 
bl rl
rm|lm-RPL
mb-RBL mp-PBL nth|rth-RPBL
rn|mn|gn-RPB
th-RP
''', 'FRPBLGTSDZ', right_to_re, right_to_basic)

def longest_word(chords):
    states = [State(root, '', False)]
    index_so_far = -1
    word_so_far = None
    for i, chord in enumerate(chords):
        if chord[0]:
            accum_str = left_to_re[chord[0]]
            for j, a in enumerate(accum_str.split('w')):
                if j != 0:
                    states = resolve_and_accum(states, 'w')
                if a:
                    states = resolve_and_accum(states, a)
        if chord[1] != '-':
            accum_str = middle_to_re[chord[1]]
            states = resolve_and_accum(states, accum_str)
        if chord[1] != '-' and chord[2]:
            if chord[2] == 'F':
                accum_str = right_to_re[chord[2]]
                states = resolve_and_accum(states, accum_str)
            else:
                has_f = 'F' in chord[2]
                accum_str = right_to_re[chord[2].replace('F', '')]
                states = resolve_and_accum(states, accum_str)
                if has_f:
                    states = resolve_and_accum(states, 'e')
        if word := check_word(states):
            index_so_far = i
            word_so_far = word
    return (index_so_far, word_so_far)

def basic_word(chords):
    to_return = ''
    for chord in chords:
        if chord[0]:
            to_return += left_to_basic[chord[0]]
        to_return += middle_to_basic[chord[1]]
        if chord[2]:
            if chord[2] == 'F':
                to_return += right_to_basic[chord[2]]
            else:
                has_f = 'F' in chord[2]
                to_return += right_to_basic[chord[2].replace('F', '')]
                if has_f:
                    to_return += 'e'
    return to_return

def lookup(key):
    print(key)
    chords = []
    if not key:
        raise KeyError
    for k in key:
        match = re.match('([STKPWHR]*)([AOEU]+)([FRPBLGTSDZ]*)$', k)
        if not match:
            match = re.match('([STKPWHR]+)(-)(F)$', k)
            if not match:
                raise KeyError
        chords.append(match.groups())
    to_return = []
    start = 0
    while start < len(chords):
        index, word = longest_word(chords[start:])
        if index == -1:
            to_return.append(basic_word(chords[start:]))
            break
        to_return.append(word)
        start += index + 1
    print(f'returning {" ".join(to_return)}')
    return ' '.join(to_return)
