#!/usr/bin/env python

import argparse
import sys
import ttfutil


usage = 'ttfc-extract [-q] [-i index] [-s scale] [-o name] <file>'
help_ = '''\
usage: {usage}

Extract font glyphs from TTF files in SVG format.
(( WIP with TTC files ))

argument:
    <file>      a TTF file

options:
    -q            be silent on success.

    -i index      extracts only index-th glyph.  Specify negative number to
                extract all glyphs.  Note that 0-th index means first glyph.
                Defaults to -1.

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
'''.format(usage=usage)

parser = argparse.ArgumentParser(add_help=False)

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
    '-i', metavar='INDEX', type=int, default=-1,
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
        print ttfutil._version

    if not len(namespace.file) == 1:
        print usage
        return 1

    with open(namespace.file[0], 'rb') as fin:
        magic = fin.read(4)
        if not magic in ('\x00\x01\x00\x00',):
            print 'This file seems to be not TTF format.'
            return 2

        try:
            t = ttfutil.dump(fin)
        except Exception as e:
            print e
            print 'Unexpected error occurred while dumping the file.'
            return 2

    if namespace.i < 0:
        start = 0
        end = t.maxp.num_glyphs
    else:
        start = namespace.i
        end = start + 1

    for i in range(start, end):
        try:
            name = t.save(i, outname=namespace.o, scale=namespace.s)
        except Exception as e:
            print e
            print 'Unexpected error occurred while drawing images.'
            return 2

        if not namespace.q:
            print 'Saved:', name

if __name__ == '__main__':
    main()
