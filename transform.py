#!/usr/bin/env python3
# -*- coding: utf8 -*-

import argparse
import codecs
import csv
from io import BytesIO
import json
import logging
import lxml.etree as ET
import os
import re
import sys
import xml.parsers.expat as xerr

from classes import ead

encodings = ['ascii', 'utf-8', 'windows-1252', 'latin-1']


#========================================
# get list of EAD files (input or output)
#========================================
def get_files_in_path(rootdir, recursive):
    result = []
    
    if recursive is True:
        print('Traversing recursively...')
        for (root, dir, files) in os.walk(rootdir):
            result.extend(
                [os.path.join(root, f) for f in files if not f.startswith('.')])
    else:
        print('Searching top folder only...')
        result = [os.path.join(rootdir, f) for f in os.listdir(
            rootdir) if not f.startswith('.') and os.path.isfile(
            os.path.join(rootdir, f))]

    print('Found {0} files to process.'.format(len(result)))
    return result


#================================================
# verify file encoding and return unicode string
#================================================
def verified_decode(f, encodings):
    print("  Checking encoding...")

    for encoding in encodings:
        bytes = codecs.open(f, mode='r', encoding=encoding, errors='strict')
        try:
            b = bytes.read()
            print('    - {0} OK.'.format(encoding))
            return b
        except UnicodeDecodeError:
            print('    - {0} Error!'.format(encoding))

    return False


#=========================
# get handles from a file
#=========================
def load_handles(handle_file):
    result = {}
    with open(handle_file, "r") as f:
        for line in csv.DictReader(f):
            id = line['identifier']
            handle = line['handlehttp']
            if id not in result:
                result[id] = handle
    return result


#=================================================
# Apply the xml transformations to the input file
#=================================================
def transform_ead(xml_as_bytes, handle):

    # in order to parse string as XML, create file-like object and parse it
    file_like_obj = BytesIO(xml_as_bytes)
    tree = ET.parse(file_like_obj)
    root = tree.getroot()

    # add missing elements
    root = add_missing_box_containers(root)
    root = add_missing_extents(root)
    root = insert_handle(root, handle)
    root = add_title_to_dao(root)
    
    # fix errors and rearrange
    root = fix_box_number_discrepancies(root)
    root = move_scopecontent(root)

    # remove duplicate, empty, and unneeded elements
    root = remove_multiple_abstracts(root)
    root = remove_empty_elements(root)
    root = remove_opening_of_title(root)
    
    return tree


#===============================================================
# Main function: Parse command line arguments and run main loop
#===============================================================
def main():
    '''The main wrapper for the transformation code -- parsing arguments, 
    reading all the files in the specified path, attempting to decode from
    various encodings, applying transrormations, and writing out both files and
    reports.'''
    border = "=" * 19
    print("\n".join(['', border, "| EAD Transformer |", border]))
    handles = load_handles('lib/ead_handles_rev.csv')
    
    # set up message logging to record actions on files
    logging.basicConfig(
        filename='data/reports/transform.log', 
        filemode='w', 
        level=logging.INFO)
    
    parser = argparse.ArgumentParser(description='Process and validate EAD.')
    parser.add_argument('-e', '--encoding', action='store_true',
        help='check encoding only of files in input path')
    parser.add_argument('-i', '--input', 
        help='input path of files to be transformed')
    parser.add_argument('-o', '--output', required=True,
        help='ouput path for transformed files')
    parser.add_argument('-r', '--resume', action='store_true', 
        help='resume job, skipping files that already exist in outpath')
    parser.add_argument('-R', '--recursive', action='store_true', 
        help='recursively process files starting at rootdirectory')
    parser.add_argument('files', nargs='*', help='files to check')

    args = parser.parse_args()
    
    # notify that resume flag is set
    if args.resume is True:
        print("Resume flag (-r) is set, will skip existing files")
    
    # notify that encoding-check-only flag is set
    if args.encoding is True:
        print("Encoding flag (-e) flag is set, will check encoding only...")
    
    # get files from inpath
    if args.input:
        input_dir = args.input
        print("Checking files in folder '{0}'...".format(input_dir))
        files_to_check = get_files_in_path(input_dir, recursive=args.recursive)
    # otherwise, use arguments for files to check
    else:
        input_dir = os.path.dirname(args.files[0])
        print(
            "No input path specified; processing files from arguments...")
        files_to_check = [f for f in args.files]
    
    # set path for output
    output_dir = args.output
    
    # loop and process each file
    for n, f in enumerate(files_to_check):
        # set up output paths and create directories if needed
        output_path = os.path.join(output_dir, os.path.relpath(f, input_dir))
        parent_dir = os.path.dirname(output_path)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
            
        # summarize file paths to screen
        print("\n{0}. Processing EAD file: {1}".format(n+1, f))
        print("  IN  => {0}".format(f))
        print("  OUT => {0}".format(output_path))
        
        # if the resume flag is set, skip files for which output file exists
        if args.resume:
            if os.path.exists(output_path) and os.path.isfile(output_path):
                print("  Skipping {0}: output file exists".format(f))
                continue
        
        # attempt strict decoding of file according to common schemes
        ead_string = verified_decode(f, encoding)

        if not ead_string:
            print("  Could not reliably decode file, skipping...".format(f))
            logging.error("{0} could not be decoded.".format(f))
            continue
            
        if args.encoding is True:
            # skip rest of loop if encoding-only flag is set and write file
            with open(output_path, 'w') as outfile:
                outfile.write(ead_string)
            continue
        
        else:
            # apply the transformations here
            # ead_tree = apply_transformations(ead_string)
            # write out result
            ead_tree.write(output_path)

if __name__ == '__main__':
    main()
