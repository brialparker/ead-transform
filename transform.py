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

from classes.ead import Ead as Ead

encodings = ['ascii', 'utf-8', 'windows-1252', 'latin-1']


#========================================
# Get list of EAD files (input or output)
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


#====================================================
# Verify file decoding and return utf8-encoded bytes
#====================================================
def verify_decoding(f, encodings):
    print("  Checking encoding...")

    for encoding in encodings:
        bytes = codecs.open(f, mode='r', encoding=encoding, errors='strict')
        try:
            b = bytes.read()
            print('    - {0} OK.'.format(encoding))
            return b.encode('utf8')
        except UnicodeDecodeError:
            print('    - {0} Error!'.format(encoding))

    return False


#=========================
# Load handles from a file
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


#===============================================================
# Main function: Parse command line arguments and run main loop
#===============================================================
def main():
    '''The main wrapper for the transformation code -- parsing arguments, 
    reading all the files in the specified path, attempting to decode from
    various encodings, applying transrormations, and writing out both files and
    reports.'''
    
    # user greeting
    border = "=" * 19
    print("\n".join(['', border, "| EAD Transformer |", border, '']))
    handles = load_handles('data/handles.csv')
    missing_handles = []
    
    # set up message logging to record actions on files
    logger = logging.basicConfig(
                format='%(asctime)s %(levelname)s %(message)s',
                filename='data/reports/transform.log', 
                filemode='w', 
                level=logging.INFO
                )
    
    
    #-----------------------------
    # Parse command line arguments
    #-----------------------------
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
    parser.add_argument('-v', '--validate', action='store_true',
        help='validate that xml is well formed')
    parser.add_argument('-s', '--schema', 
        help='XSD to validate against')
    parser.add_argument('files', nargs='*', 
        help='files to check')
    args = parser.parse_args()
    
    # notify that resume flag is set
    if args.resume is True:
        print("Resume flag (-r) is set, will skip existing files")
    
    # notify that encoding-check flag is set
    if args.encoding is True:
        print("Encoding flag (-e) flag is set, checking encoding ...")
    
    # notify that validation-check flag is set
    if args.validate is True:
        print("Validation flag (-v) flag is set, checking well-formedness ...")
    
    # load XSD to validate against
    if args.schema:
        schema_xml = ET.parse(args.schema)
        ead_schema = ET.XMLSchema(schema_xml)
        ead_parser = ET.XMLParser(schema=ead_schema)
    
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
    
    
    #---------------------------------------
    # Main loop  for processing each EAD XML
    #---------------------------------------
    for n, f in enumerate(files_to_check):
    
        # set up output paths and create directories if needed
        output_path = os.path.join(output_dir, os.path.relpath(f, input_dir))
        basename = os.path.basename(f)
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
        ead_bytes = verify_decoding(f, encodings)
        
        if not ead_bytes:
            print("  Could not reliably decode {0}, skipping...".format(f))
            logging.error("{0} could not be decoded.".format(f))
            continue
            
        if args.encoding is True:
            # validate XML and write to file
            if args.validate is True:
                file_like_obj = BytesIO(ead_bytes)
                try:
                    ead_tree = ET.parse(file_like_obj)
                    # ead_schema.assertValid(ead_tree)
                    ead_tree.write(output_path)
                except:
                    # logging.error(xmlschema.error_log.last_error)
                    print("  Could not parse XML in {0}, skipping...".format(f))
                    logging.error("{0} is malformed XML.".format(f))
                    
            # write decoded bytes to file without validation
            else:
                with open(output_path, 'wb') as outfile:
                    outfile.write(ead_bytes)
            continue
        
        else:
            if basename in handles.keys():
                handle = handles[basename]
            else:
                missing_handles.append(basename)
                handle = ''
            
            # create an EAD object
            print("  Parsing XML...")
            ead = Ead(basename, handle, BytesIO(ead_bytes))
            
            # add missing elements
            ead.add_missing_extents()
            ead.correct_text_in_extents()
            ead.add_missing_box_containers()
            ead.insert_handle()
            ead.add_title_to_dao()
            
            # remove duplicate, empty, and unneeded elements
            ead.remove_multiple_abstracts()
            ead.remove_empty_elements()
            ead.remove_opening_of_title()

            # fix errors and rearrange
            ead.fix_box_number_discrepancies()
            ead.move_scopecontent()
            ead.sort_containers()

            # write out result
            ead.tree.write(output_path, 
                           pretty_print=True, 
                           encoding='utf-8', 
                           xml_declaration=True
                           )
            

    # print(missing_handles)

if __name__ == '__main__':
    main()
