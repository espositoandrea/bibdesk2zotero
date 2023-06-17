#!/usr/bin/env python3

#
# This little program reads in a BibDesk BibTex file and writes it out with the
# the quirky file locations (Base64 encoded plists) written as simple paths that 
# can be understood by Zotero.
#
# For this to work you'll need to install pybtex.
# 
# usage: ./bibdesk2zotero.py citations.bib /path/to/files > citations-new.db
#

import os
import argparse
import re
import sys
import base64
import pathlib
import plistlib
import unicodedata
import pybtex.database

from pybtex.utils import OrderedCaseInsensitiveDict


def main():
    parser = argparse.ArgumentParser(description='A utility for rewriting'
                                     ' BibDesk BibTeX files so that they can'
                                     ' be read by Zotero with the file'
                                     ' references intact')
    parser.add_argument('database',
                        help="The BibDesk BibTeX file",
                        type=argparse.FileType('r'),
                        default=sys.stdin,
                        nargs='?')
    parser.add_argument('--path', '-p',
                        help="Path to the root folder for file searching",
                        type=pathlib.Path)
    parser.add_argument('--out', '-o',
                        help="Output file",
                        type=argparse.FileType('w'),
                        default=sys.stdout)
    args = parser.parse_args()
    if args.path is None:
        if args.database is sys.stdin:
            raise parser.error("Cannot guess path from stdin. Please specify"
                               " --path")
        args.path = pathlib.Path(args.database.name).parent.absolute()

    new_bib = convert(args.database, args.path)
    print(new_bib, file=args.out)
    args.database.close()
    args.out.close()


def convert(bib_file, base_dir):
    db = pybtex.database.parse_file(bib_file, bib_format="bibtex")

    for key in db.entries:
        entry = db.entries[key]
        for field_name in entry.fields:
            m = re.match('^[Bb]dsk-[Ff]ile-(\d+)$', field_name)
            if m:
                bdsk = entry.fields[field_name]
                bdsk_decoded = base64.b64decode(bdsk)
                plist = plistlib.loads(bdsk_decoded)
                file_path = base_dir / unicodedata.normalize('NFC', plist['relativePath'])

                if m.group(1) == '1':
                    new_field_name = 'File'
                else:
                    new_field_name = 'File-' + m.group(1)
               
                # Strangely pybtex.database.Entry objects don't allow fields to be deleted. 
                # This little workaround converts the fields to a normal dictionary and 
                # then modifies it, and assigns the fields back to the entry again.
                #
                # See this issue for more:
                # https://bitbucket.org/pybtex-devs/pybtex/issues/57/

                fields = dict(entry.fields)
                fields[new_field_name] = str(file_path)
                fields.pop(field_name)
                entry.fields = fields

    return db.to_string('bibtex')


if __name__ == "__main__":
    main()
