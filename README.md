# Right E Steno

An English-language stenographic theory for machine shorthand, and an
implementation of that theory in the form of a Python dictionary for use with
[Plover](https://github.com/openstenoproject/plover) and
[`plover_python_dictionary`](https://github.com/benoit-pierre/plover_python_dictionary).

This theory and dictionary still has a lot of rough edges, but as of the time
of writing, I do intend to develop this into something I will regularly use to
write. But in the meantime, if you're interested in theory development, and a
theory that has an unorthodox right bank, an orthographic basis, flexible
chording, and no usage of asterisks interests you, take a look!

## Quick start

You will need a word list. If you do not have one at `/usr/share/dict/words`,
change the path in the Python file to point to one.

If you have Python 3 installed, you can run the Python file standalone. For
example:

    $ python3 -i right-e-steno.py 
    >>> lookup(['HEL', 'O', 'PHRO', 'STPER'])
    'hello plover'

If you have Plover and `plover_python_dictionary`, you can also install this
file as a dictionary.

## Explanation of the theory

    Left bank     Right bank
    S T P H *   * F P L T D
    S K W R *   * R B G S Z
    
          Vowel keys
          A O   E U

Each stroke is one or more keys from the _left bank_, the _vowel keys_, and/or
the _right bank_ simultaneously pressed and released. Every sequence of strokes
is converted into a _pattern_, and the first word in the word list that matches
that pattern will be output. (For this reason, if you have a frequency list of,
say, your own writing, you should sort the word list with higher-frequency
words first.)

This theory recognizes strokes that have at least one vowel key. Within each
stroke, the meaning of each key is as follows:

* Left bank
  * TODO: Write this. For now, see `left_to_re` in the Python file.
* Vowel keys
  * `A` matches "a". Likewise for `O`, `E`, and `U`.
  * `EU` matches "i" and "y".
  * Two-vowel combinations are as follows. In all these cases, anything that
    matches "i" also matches "y", and anything that matches "u" also matches
    "w".
    * Combinations involving "i": `AEU` (that is, `A` plus the pair of vowels
      on the other side) matches any combination of "a" and "i" (that is, "ai"
      and "ia"). Likewise for "o", "e", and "u".
    * Combinations not involving "i": `AO` matches any combination of "a" and
      "o". Likewise for all other combinations, except "eu"/"ue" which is
      matched by `AOEU` (because `EU` is already taken).
    * "ee" is also matched by `AOU`, and "oo" by `AU`.
* Right bank
  * If the only key from the right bank is `F`, it matches "gh" or "h".
  * Otherwise:
    * If `F` is present, it matches "e" _after_ any other consonants from the
      right bank.
    * As for the other consonants, TODO: Write this. For now, see `right_to_re`
      in the Python file.

This theory also recognizes strokes that consist only of one or more consonants
from the left bank and `F` from the right bank. Such strokes are treated as a
consonant cluster, interpreted the same way as the "Left bank" list element
above.

Sequences of strokes can be interrupted by strokes that this theory does not
recognize. Typically, these are consonant-only strokes handled by Plover that
represent punctuation or very common phrases like "of the".

If a sequence of strokes does not match any word, this theory splits the
strokes into two sequences in such a way that the left sequence has as many
strokes as possible yet still matches a word, and repeats the process with the
right sequence.

This theory has no notion of syllables. For example, one could write "siege" as
one stroke (`SAOEFG`) or as multiple strokes (`SAOEG/E`, `SAOE/TKPWE`, or even
`SEU/EFG`).

## Phonetic versus orthographic

This project was originally intended to create, from the ground up, a
dictionary for the Plover theory (the theory that comes with the Plover
software), a theory that relies on the pronunciation of words. There are
several sets of words in English that are pronounced the same but spelled
differently, and Plover theory has ways to disambiguate them based on their
spelling. So at least for a certain number of words, paying attention to
orthography is unavoidable.

In addition, there are many words that I know how to spell but not pronounce,
and the ones that I do pronounce I sometimes pronounce differently to others.

For these reasons, I thought it would be worth trying to build a theory that is
not phonetic at all, hence this project.

## Note

This is not an officially supported Google product.
