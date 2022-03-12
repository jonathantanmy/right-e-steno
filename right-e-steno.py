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

"""
Right E steno theory.
"""

from __future__ import annotations
import bisect
import re
import typing
import sys
from dataclasses import dataclass, field

LONGEST_KEY = 10


@dataclass
class Alt:
    choices: list[Pat]

    def __repr__(self) -> str:
        return "alt(" + ", ".join(repr(c) for c in self.choices) + ")"


@dataclass
class Seq:
    elements: list[Pat]

    def __repr__(self) -> str:
        return "seq(" + ", ".join(repr(e) for e in self.elements) + ")"


Pat = typing.Union[Alt, Seq, str]


def alt(*args: Pat) -> Pat:
    """Matches one of the given choices.

    >>> alt() # will never match
    alt()

    >>> alt('a')
    'a'

    >>> alt(alt('b', 'c'), 'd')
    alt('b', 'c', 'd')
    """
    choices = []
    for a in args:
        if isinstance(a, Alt):
            choices.extend(a.choices)
        else:
            choices.append(a)
    if len(choices) == 1:
        return choices[0]
    return Alt(choices)


def seq(*args: Pat) -> Pat:
    """Matches all given elements sequentially.

    >>> seq()
    seq()

    >>> seq('a')
    'a'

    >>> seq(seq('b', 'c'), 'd')
    seq('b', 'c', 'd')
    """
    elements = []
    for a in args:
        if isinstance(a, Seq):
            elements.extend(a.elements)
        else:
            elements.append(a)
    if len(elements) == 1:
        return elements[0]
    return Seq(elements)


def compile_pat_part(patstr: str) -> tuple[Pat, str]:
    """Compile until an unmatched ')' or end of string.

    >>> compile_pat_part("a(b|c)")
    (seq('a', alt('b', 'c')), '')

    >>> compile_pat_part("d)e")
    ('d', 'e')
    """
    ret = alt()
    current_seq = seq()
    while patstr:
        if patstr[0] == "(":
            inner_pat, remaining_patstr = compile_pat_part(patstr[1:])
            current_seq = seq(current_seq, inner_pat)
            patstr = remaining_patstr
        elif patstr[0] == "|":
            ret = alt(ret, current_seq)
            current_seq = seq()
            patstr = patstr[1:]
        elif patstr[0] == ")":
            patstr = patstr[1:]
            break
        else:
            current_seq = seq(current_seq, patstr[0])
            patstr = patstr[1:]
    ret = alt(ret, current_seq)
    return ret, patstr


def compile_pat(patstr: str) -> Pat:
    """Compile into a pattern.

    >>> compile_pat("a(b|c)")
    seq('a', alt('b', 'c'))

    >>> compile_pat("d)e")
    Traceback (most recent call last):
        ...
    ValueError: unbalanced parentheses
    """
    pat, rest = compile_pat_part(patstr)
    if rest:
        raise ValueError("unbalanced parentheses")
    return pat


@dataclass
class Cursor:
    word_list: list[str] = field(repr=False)
    matching_range: range
    letters_read: str = ""
    score: int = 0

    def on_word(self) -> bool:
        """Return whether letters_read is in the word list."""
        return self.word_list[self.matching_range.start] == self.letters_read

    def advance_any_letter(self, letters: str, /, add_score=0) -> list:
        """Advance by any of the letters in the string.

        >>> word_list = ['a', 'ab', 'ac', 'ad', 'b']
        >>> cursor_start = Cursor(word_list, range(len(word_list)))
        >>> cursor_a = cursor_start.advance_any_letter('a', add_score=10)
        >>> cursor_a
        [Cursor(matching_range=range(0, 4), letters_read='a', score=10)]

        >>> cursor_bc = cursor_a[0].advance_any_letter('bc', add_score=20)
        >>> cursor_bc
        [Cursor(matching_range=range(1, 2), letters_read='ab', score=30),
         Cursor(matching_range=range(2, 3), letters_read='ac', score=30)]
        """
        ret = []
        for letter in list(letters):
            start_needle = self.letters_read + letter
            stop_needle = self.letters_read + chr(ord(letter) + 1)
            start = bisect.bisect_left(
                self.word_list,
                start_needle,
                lo=self.matching_range.start,
                hi=self.matching_range.stop,
            )
            stop = bisect.bisect_left(
                self.word_list,
                stop_needle,
                lo=self.matching_range.start,
                hi=self.matching_range.stop,
            )
            if start != stop:
                ret.append(
                    Cursor(
                        self.word_list,
                        range(start, stop),
                        start_needle,
                        self.score + add_score,
                    )
                )
        return ret

    def advance(self, pat: Pat) -> list:
        """Advance by the given pattern.

        Returned cursors may overlap:

        >>> word_list = ['a', 'ab', 'ac', 'ad', 'b']
        >>> cursor = Cursor(word_list, range(len(word_list)))
        >>> cursor.advance(seq('a', alt(seq(), 'b', 'c')))
        [Cursor(matching_range=range(0, 4), letters_read='a', score=0),
         Cursor(matching_range=range(1, 2), letters_read='ab', score=0),
         Cursor(matching_range=range(2, 3), letters_read='ac', score=0)]

        The ! matches 0 to 2 vowels, with a score of 10 per vowel.

        >>> word_list = ['c', 'cac', 'cc', 'ceic', 'couac']
        >>> cursor = Cursor(word_list, range(len(word_list)))
        >>> cursor.advance(seq('c', '!', 'c'))
        [Cursor(matching_range=range(2, 3), letters_read='cc', score=0),
         Cursor(matching_range=range(1, 2), letters_read='cac', score=10),
         Cursor(matching_range=range(3, 4), letters_read='ceic', score=20)]

        The E optionally matches 'e', with a score of 100 if it does.

        >>> word_list = ['c', 'ce']
        >>> cursor = Cursor(word_list, range(len(word_list)))
        >>> cursor.advance(seq('c', 'E'))
        [Cursor(matching_range=range(0, 2), letters_read='c', score=0),
         Cursor(matching_range=range(1, 2), letters_read='ce', score=100)]

        The W optionally matches one of 'aeiouw', with a score of 1 if it does.

        >>> word_list = ['c', 'ce', 'cf', 'cw']
        >>> cursor = Cursor(word_list, range(len(word_list)))
        >>> cursor.advance(seq('c', 'W'))
        [Cursor(matching_range=range(0, 4), letters_read='c', score=0),
         Cursor(matching_range=range(1, 2), letters_read='ce', score=1),
         Cursor(matching_range=range(3, 4), letters_read='cw', score=1)]

        All lowercase vowels match themselves. All lowercase consonants match
        single or double versions of themselves.

        >>> word_list = ['aab', 'aabb', 'ab', 'abb']
        >>> cursor = Cursor(word_list, range(len(word_list)))
        >>> cursor.advance(seq('a', 'b'))
        [Cursor(matching_range=range(2, 4), letters_read='ab', score=0),
         Cursor(matching_range=range(3, 4), letters_read='abb', score=0)]
        """
        ret = []
        if isinstance(pat, str):
            if pat == "!":
                no_vowels = [self]
                one_vowel = self.advance_any_letter("aeiou", add_score=10)
                two_vowels = []
                for ov in one_vowel:
                    two_vowels.extend(ov.advance_any_letter("aeiou", add_score=10))
                return no_vowels + one_vowel + two_vowels
            if pat == "E":
                return [self] + self.advance_any_letter("e", add_score=100)
            if pat == "W":
                return [self] + self.advance_any_letter("aeiouw", add_score=1)
            one_letter = self.advance_any_letter(pat)
            if not one_letter:
                return []
            if pat in "aeiou":
                return one_letter
            return one_letter + one_letter[0].advance_any_letter(pat)
        if isinstance(pat, Alt):
            new_cursors = []
            for choice in pat.choices:
                new_cursors.extend(self.advance(choice))
            return new_cursors
        if isinstance(pat, Seq):
            old_cursors = [self]
            new_cursors = []
            for e in pat.elements:
                for c in old_cursors:
                    new_cursors.extend(c.advance(e))
                old_cursors, new_cursors = new_cursors, []
            return old_cursors
        raise ValueError("unexpected type of pat")


def advance_flatten(cursors: list[Cursor], pat: Pat) -> list[Cursor]:
    """Convenience function to advance a list of cursors."""
    ret = []
    for c in cursors:
        ret.extend(c.advance(pat))
    return ret


def get_word(cursors: list[Cursor]) -> typing.Optional[str]:
    """Return the lowest-score word."""
    best_word = None
    best_score = sys.maxsize
    for c in cursors:
        if c.on_word() and c.score < best_score:
            best_word = c.letters_read
            best_score = c.score
    return best_word


def make_dict(s: str) -> dict[str, str]:
    ret = {}
    for k, v in (kv.split("=") for kv in s.split()):
        ret[k] = v
    return ret


def compile_columns(s: str) -> dict[str, Pat]:
    r"""Given chords and their associated pats, return all possible ways of
    combining them.

    A column is a set of keys on a stenotype. A chord spans one or more
    columns. Chords are arranged in lines, with line N containing all chords
    that span no further than column N. Here's an example with the columns "S",
    "TK", "P", and "HR".

    >>> c = compile_columns('S=s\nT=t K=k\nP=p KP=g\nH=h R=r PH=m SR=v')

    The pats of combined chords are intercalated with '!', as can be seen in
    the examples below.

    Chords cannot be combined if their columns overlap. For example, SR would
    normally be "v", but STR would not be "vt" or "tv" because SR spans the
    column T is in.  Instead, the pat for S|T|R is used.

    >>> c['SR']
    'v'
    >>> c['STR']
    seq('s', '!', 't', '!', 'r')

    When more than one set of columns correspond to a chord, the set with the
    largest rightmost column is chosen. In this example, K|PH is chosen over
    KP|H.

    >>> c['KPH']
    seq('k', '!', 'm')
    """
    cumul_column_to_chord_to_pat = {}
    for d in (make_dict(x) for x in (x.strip() for x in s.split("\n")) if x):
        chord_to_pat = {}
        for chord, patstr in d.items():
            pat = compile_pat(patstr)
            chord_to_pat[chord] = pat
            # Also, combine the current pat with items from cumulative columns
            # that do not intersect with the current chord.
            for cumul_column, cp in cumul_column_to_chord_to_pat.items():
                if set(chord).intersection(cumul_column):
                    continue
                for chord0, pat0 in cp.items():
                    chord_to_pat[chord0 + chord] = seq(pat0, "!", pat)
        cumul_column_to_chord_to_pat[str(set("".join(chord_to_pat)))] = chord_to_pat
    ret = {"": seq()}
    for d in cumul_column_to_chord_to_pat.values():
        ret.update(d)
    return ret


left_chord_to_pat = compile_columns(
    """
+=e|i|a|o|u
S=s|ex
T=t K=k|c|g TK=d STK=x
P=p W=w PW=b TP=f|ph KP=g KW=q(|u) TPKW=c SPW=z
H=h R=r HR=l PH=m TPH=n KWR=y SKWR=j SR=v
"""
)
# + alone matches nothing. (It is used as a continuation key.)
left_chord_to_pat["+"] = seq()
# Because HR=l, add techniques to write "hr".
for x in ("S", "T"):
    left_chord_to_pat[x + "WR"] = alt(
        left_chord_to_pat[x + "WR"], seq(left_chord_to_pat[x], "!", "h", "r")
    )
for x in ("K", "KP", "TPKW"):
    left_chord_to_pat[x + "R"] = alt(
        left_chord_to_pat[x + "R"], seq(left_chord_to_pat[x], "!", "h", "r")
    )
# PH can be "n" sometimes.
left_chord_to_pat["KPH"] = alt(
    left_chord_to_pat["KPH"], seq(left_chord_to_pat["K"], "!", "n")
)

right_chord_to_pat = compile_columns(
    """
P=p B=b PB=n
L=l G=g(|h)|h LG=c(|h|k) PL=m|p!l BG=k PG=y
T=t
S=s GS=(|c)tion|sion|cean BGS=x|k!s
D=d TD=th
Z=e
"""
)
# F and R need special handling.
for chord, pat in list(right_chord_to_pat.items()):
    F_prioritize_v = chord == "Z"
    F_can_be_s = set(chord).intersection("PBLGT")
    R_can_be_l = set(chord).intersection("PB")
    FR_can_be_m = set(chord).intersection("PBLG") not in [set("PL"), set("BG")]
    FR_can_be_n = set(chord).intersection("PBLG") == set("BG")

    F_pat = alt("v", "f") if F_prioritize_v else alt("f", "v")
    if F_can_be_s:
        F_pat = alt(F_pat, "s")
    R_pat = alt("r", "l") if R_can_be_l else "r"
    FR_pat = alt(seq(F_pat, "!", R_pat), seq(R_pat, "!", F_pat))
    if FR_can_be_m:
        FR_pat = alt(FR_pat, "m")
    if FR_can_be_n:
        FR_pat = alt(FR_pat, "n")
    right_chord_to_pat["F" + chord] = seq(F_pat, "!", right_chord_to_pat[chord])
    # R can appear before or after the rest of the chord.
    right_chord_to_pat["R" + chord] = alt(
        seq(R_pat, "!", right_chord_to_pat[chord]),
        seq(right_chord_to_pat[chord], "!", "r"),
    )
    right_chord_to_pat["FR" + chord] = alt(
        seq(FR_pat, "!", right_chord_to_pat[chord]),
        seq(F_pat, "!", right_chord_to_pat[chord], "!", "r"),
    )
right_chord_to_pat["Z"] = "z"

THREE_VOWELS = {
    "A": ["ee", "ui"],
    "O": ["ii", "ue"],
    "E": ["aa", "uo"],
    "U": ["oo", "au"],
}


def get_vowel_clusters(middle_chord: str) -> list[str]:
    if middle_chord == "AOEU":
        # TODO: "oo" can be specified in 2 ways. See if we should remove one.
        return ["oo"]
    if len(middle_chord) == 3:
        return THREE_VOWELS[next(iter(set("AOEU").difference(set(middle_chord))))]
    if middle_chord == "OE":
        return ["u", "oe"]
    return [middle_chord.replace("U", "i").lower()]


def vowels_to_pat(vowels: str) -> Pat:
    """Compile the given vowels into a pattern. 'i' can also represent 'y'. 'u'
    can also represent 'w' except in the first position.

    >>> vowels_to_pat('iu')
    seq(alt('i', 'y'), alt('u', 'w'))
    """
    vowels = vowels.replace("i", "(i|y)")
    if len(vowels) > 1:
        vowels = vowels[0] + vowels[1:].replace("u", "(u|w)")
    return compile_pat(vowels)


def compile_vowel_clusters(vcs: list[str]) -> Pat:
    """Compile all vowel clusters into one pattern that matches any of them.

    A 2-length vowel cluster is considered to represent those vowels in either
    order, plus an optional third vowel. The behavior of vowels_to_pat() is
    also applied.

    >>> compile_vowel_clusters(['ui'])
    seq(alt(seq('u', alt('i', 'y')), seq(alt('i', 'y'), alt('u', 'w'))),
        alt(seq(), 'W'))
    """
    choices = []
    for vc in vcs:
        if len(vc) == 2:
            if vc[0] == vc[1]:
                choice = vowels_to_pat(vc)
            else:
                choice = alt(vowels_to_pat(vc), vowels_to_pat(vc[::-1]))
            choices.append(seq(choice, alt(seq(), "W")))
        else:
            choices.append(vowels_to_pat(vc))
    return alt(*choices)


islands = {}

for k, v in make_dict(
    """
=
T=to
PW=but
K=can
TW=between
SK=since
TP=for
W=with
SPW=because
KPW=become
TH=that
TKPW=about
TKHR=already
TWR-F=through
S-R=should
K-R=could
W-R=would
"""
).items():
    islands["^" + k] = v
    hyphen = "" if "-" in k else "-"
    for k1, v1 in (("", ""), ("F", "of ")):
        if "-" in k and k1:
            continue
        for k2, v2 in (("", ""), ("B", "be "), ("PB", "and ")):
            for k3, v3 in (("", ""), ("T", "the "), ("TS", "a ")):
                if not v1 and not v2 and not v3:
                    continue
                islands[k + hyphen + k1 + k2 + k3] = (v + v1 + v2 + v3).strip()

islands["*PB"] = "{^}n't"
islands["*S"] = "{^}'s"
islands["*P"] = "{^}'"
islands["*L"] = "{^}'ll"
islands["*F"] = "{^}'ve"
islands["*T"] = "{^}'t"
islands["*R"] = "{^}'re"
islands["*PL"] = "{^}'m"
islands["*D"] = "{^}'d"
islands["-PG"] = "I"
islands["SKWRAURBGS"] = "{^}{-|}"
islands["TK-P"] = "{^}"  # don't space
islands["S-P"] = "{^ ^}"
islands["K-P"] = "{-|}"
islands["TP-PL"] = "{.}"
islands["KW-BG"] = "{,}"
islands["KW-PL"] = "{?}"
islands["TP-BG"] = "{!}"
islands["H-P"] = "{^}-{^}"
islands["TK-FG"] = "-"
islands["SKWR-RBGS"] = "{;}"
islands["+TPH-FPLT"] = "{:}"
islands["HR-PS"] = "{^...^}"
islands["TP-PLT"] = '{^."}{-|}'
islands["TP-PLD"] = '{^. "^}{-|}'
islands["KW-BGT"] = '{^,"}'
islands["KW-BGD"] = '{^, "^}{-|}'
islands["KPW-S"] = "becomes"


def untuck_right_vowel(
    cursors: list[Cursor], vcs: list[str], right_chord: str
) -> list[Cursor]:
    """Return cursors representing what would happen if the 'i' in vowel
    clusters were untucked such that the 'i' appeared after the right pattern.

    If the vowel cluster is of length 2, an additional vowel is permitted
    before the right pattern, with an additional score of 1.

    >>> word_list = ['aty', 'auty']
    >>> cursor = Cursor(word_list, range(len(word_list)))
    >>> untuck_right_vowel([cursor], ['ai'], 'T')
    [Cursor(matching_range=range(0, 1), letters_read='aty', score=0),
     Cursor(matching_range=range(1, 2), letters_read='auty', score=1)]

    >>> word_list = ['ty', 'uty']
    >>> cursor = Cursor(word_list, range(len(word_list)))
    >>> untuck_right_vowel([cursor], ['i'], 'T')
    [Cursor(matching_range=range(0, 1), letters_read='ty', score=0)]
    """
    ret = []
    for vc in vcs:
        if "i" in vc:
            to_add = advance_flatten(cursors, vowels_to_pat(vc.replace("i", "", 1)))
            if len(vc) > 1:
                to_add = advance_flatten(to_add, "W")
            to_add = advance_flatten(to_add, right_chord_to_pat[right_chord])
            to_add = advance_flatten(to_add, vowels_to_pat("i"))
            ret += to_add
    return ret


def handle_ing(cursors: list[Cursor], vcs: list[str], right_chord: str) -> list[Cursor]:
    """Handle the special case in which the middle is empty and the right chord
    is only G.
    """
    if vcs != [""] or right_chord != "G":
        return []
    return advance_flatten(cursors, seq("i", "n", "g"))


fragments = {}
fragments["KWR"] = "you"
fragments["KWR-R"] = "your"
fragments["KWR-RS"] = "yours"
fragments["W"] = "with"

WORDS = []
with open("/home/jonathan/words") as f:
    for rawline in f:
        if m := re.match("([a-z]+)$", rawline):
            WORDS.append(m.group(1))


def lookup(key):
    """
    >>> lookup(['HEL', 'O'])
    'hello'
    >>> lookup(['PHRO', 'SRER'])
    'plover'
    >>> lookup(['TKUFRPBT'])
    'different'
    """
    cursors = [Cursor(WORDS, range(len(WORDS)))]
    inhibit_vowel_insertion = True
    """If False, a ! will be inserted if the syllable does not start with a
    vowel.
    """
    for i, k in enumerate(key):
        if k in fragments:
            # Fragments always allow vowel insertion.
            if not inhibit_vowel_insertion:
                cursors = advance_flatten(cursors, "!")
            inhibit_vowel_insertion = False
            continue
        if k in islands:
            if len(key) == 1:
                return islands[k]
            raise KeyError
        if match := re.match("[+STKPWHR]+$", k):
            left = match.group(0)
            middle = ""
            right = ""
        elif match := re.match("([+STKPWHR]*)([AOEU-]+)([FRPBLGTSDZ]*)$", k):
            left = match.group(1)
            middle = match.group(2).replace("-", "")
            right = match.group(3)
        else:
            raise KeyError
        if not left and middle and right and i:
            # Vowel and Right must start word
            raise KeyError
        if "+" in left and left != "+" and i:
            # + and anything else in Left must start word
            raise KeyError
        if not inhibit_vowel_insertion and (left or not middle):
            cursors = advance_flatten(cursors, "!")
        cursors = advance_flatten(cursors, left_chord_to_pat[left])
        vcs = get_vowel_clusters(middle)
        cursors = (
            advance_flatten(
                cursors, seq(compile_vowel_clusters(vcs), right_chord_to_pat[right])
            )
            + (untuck_right_vowel(cursors, vcs, right) if i == len(key) - 1 else [])
            + (
                advance_flatten(cursors, seq("i", "n", "g"))
                if not middle and right == "G"
                else []
            )
        )
        inhibit_vowel_insertion = middle and not right
    cursors = advance_flatten(cursors, "E")
    word = get_word(cursors)
    if not word:
        raise KeyError
    return word


if __name__ == "__main__":
    import doctest

    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
