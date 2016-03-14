#!/usr/bin/env python

import argparse
import os
import sys
import ttfutil

_version = '0.2'


usage = (
    'ttfc-extract [options] <file>\n'
    "`ttfc-extract -h' for help message."
)
help_ = '''usage: ttfc-extract [options] <file>

Extract font glyphs from TTF/TTC files in SVG format.

argument:
    <file>      either a TTF or a TTC file

options:
    -h, --help    shows this message

    -v, --version
                  shows version number

    -q            be silent on success

    -g index      extracts only index-th glyph.  Specify negative number to
                extract all glyphs.  Note that 0-th index means first glyph.
                Defaults to -1.

    -f index      extracts only index-th fonts (with TTC only); like -g.

    -s scale      scales the vectors.  Defaults to 0.10.

    -o name       specifies the name of output file.  You can use the following
                variables:

                    {{gname}}: name of the glyph
                    {{fname}}: name of the font
                    {{index}}: index

                Note that you can use python-style format, like:

                    0x{{index:0>4x}}
                    {{index:0>4}}

                To use either `{{' or `}}', you have to escape them as `{{{{'
                and `}}}}', respectively.  Defaults to `{{index}}.svg'.

original-maintainer:
    https://github.com/rsk0315
    https://twitter.com/rsk0315_h4x
'''


parser = argparse.ArgumentParser(
    add_help=False,
    usage=usage,
)

parser.add_argument(
    '-h', '--help', action='store_true', default=False,
)
parser.add_argument(
    '-v', '--version', action='store_true', default=False,
)
parser.add_argument(
    '-q', action='store_true', default=False,
)
parser.add_argument(
    '-g', metavar='INDEX', type=int, default=-1,
)
parser.add_argument(
    '-f', metavar='INDEX', type=int, default=-1,
)
parser.add_argument(
    '-s', metavar='SCALE', type=float, default=0.10,
)
parser.add_argument(
    '-o', metavar='name', default='{index}.svg',
)

parser.add_argument(
    'file', metavar='FILE', nargs='*',
)

def main():
    namespace = parser.parse_args()
    if namespace.help:
        print help_
        return 0

    if namespace.version:
        print (
            'ttfc-extract {}\n'
            'Copyright (C) 2016 @rsk0315_h4x'
        ).format(_version)
        return 0

    if not len(namespace.file) == 1:
        print usage
        return 1

    with open(namespace.file[0], 'rb') as fin:
        magic = fin.read(4)

        if magic in ('true', '\x00\x01\x00\x00'):
            try:
                ttf = ttfutil.TTFObject(fin)
            except Exception as e:
                print e
                print 'Unexpected error occurred while reading the TTF file.'
                return 2

            ttfs = (ttf,)

        elif magic in ('ttcf',):
            try:
                ttc = ttfutil.TTCObject(fin)
            except Exception as e:
                print e
                print 'Unexpected error occurred while reading the TTC file.'
                return 2

            ttfs = ttc.ttfs
            if namespace.f > -1:
                if namespace.f < len(ttfs):
                    ttfs = (ttfs[namespace.f],)
                else:
                    ttfs = ()

        elif magic in ('typ1', 'OTTO'):
            print 'This program cannot handle the font format.\n'
            print 'Magic: {!r} {!r} {!r} {!r}'.format(*magic)
            return 2

        else:
            print 'This file is written in unexpected format.\n'
            print 'Magic: {!r} {!r} {!r} {!r}'.format(*magic)
            return 2


    options = {
        'outname': namespace.o,
        'scale': namespace.s,
    }

    for ttf_ in ttfs:
        if namespace.g < 0:
            start = 0
            end = ttf_.maxp.num_glyphs
        else:
            start = namespace.g
            end = start + 1

        for i in range(start, end):
            try:
                name = ttf_.save(i, **options)
            except Exception as e:
                print e
                print 'Unexpected error occurred while saving SVGs.'
                raise e
                return 2

            if not namespace.q:
                print 'Saved:', name


if __name__ == '__main__':
    main()
