# Right E Steno

An English-language stenographic theory for machine shorthand, and an
implementation of that theory in the form of a Python dictionary for use with
[Plover](https://github.com/openstenoproject/plover) and
[`plover_python_dictionary`](https://github.com/benoit-pierre/plover_python_dictionary).

This theory and dictionary is a work in progress.

## What you might find interesting

First, this is an orthographic theory. In phonetic theories, we ask what sound
a `T` represents, but here, we ask what letter(s) a `T` matches. (In this
theory, it matches "t" or "tt".)

A corollary of this is that in this theory, the way vowels are written are
different to some other theories. They are based neither on their pronunciation
nor on which syllable the stress falls in the word.

One specific thing about vowels that I wanted to call out: in some other
theories, non-stressed vowels may be omitted.  The equivalent feature in this
theory is automatic matching of vowels in between fragments of left bank and
right bank patterns.  For example, "different" is stroked `TKUFRPBT`: in
between the `F` and `R` and the `R` and `PB` (and the `PB` and `T`, although
this is not used here), up to two vowels are automatically allowed (in each
space).

Second, especially for theory crafters, the way I have implemented this theory
might be interesting: there is no mapping of whole chords to whole words
anywhere.  Instead, I am using a mapping of chord fragments to pattern
fragments, and checking the stitched-together pattern against all the words in
the user-given word list (operating on the data structure as a whole).

## Quick start

You will need a word list (e.g. `/usr/share/dict/words`). Change the path in
the Python file to point to it.

If you have Python 3 installed, you can run the Python file standalone. For
example:

    $ python3 -i right-e-steno.py 
    >>> lookup(['HEL', 'O'])
    'hello'

If you have Plover and `plover_python_dictionary`, you can also install this
file as a dictionary.

## Explanation of the theory

TBD (the theory still may change)

In the meantime, the Python implementation is commented with some Python
doctest examples.

## Future work

Probably the most important thing is to understand what chords are needed to
write regular words, and in doing so, understand what chords are free for
briefs and phrases. Currently, I'm reserving chords that have no vowels and
that have right bank keys (except for "-S", "-D", "-G", and "-GS", all of which
are used to write common word suffixes) for briefs and phrases, but I would
like to relax this restriction. In particular, I would like to be able to write
briefs and phrases with vowels too.

I am also reserving all chords of the form "empty-left-bank vowel right-bank"
(e.g. "UPB") as chords that must start words. Maybe that restriction could be
relaxed too.

In order to do this, I probably will need to make a list of common words and
the chording that comes most naturally to me, and then see what chords are
actually used.

Some more things:

* Currently `GT` matches "ght" and `TD` matches "th", but I'm thinking of
  making `GT` match both. This, in particular, frees `TD` to match "t!d". (The
  "!" represents up to two vowels.)

* Make `D` and `S` produce the true past tense and plural, instead of just
  appending "d" and "s". This will make words like "planned" easier to write
  (`PHRAPB/-D` writes "planed", because the single "n" has precedence.)

* Figure out a way to write common phrases. (There are some in there currently,
  but not many.)
