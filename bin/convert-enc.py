#!/usr/bin/env python3

import codecs
import sys

inputfile = sys.argv[1]
outputfile = sys.argv[2]

with open(inputfile, 'rb') as f1:
    file = f1.read().decode('latin1', 'ignore') 
    print(file)
    
with open(outputfile, 'w') as f2:
    f2.write(file)
