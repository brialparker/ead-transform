#!/usr/bin/env python3

from lxml import etree

root = etree.Element("doc")
doc = etree.ElementTree(root)

for n in range(10):
    tag = "child" + str(n)
    child = etree.SubElement(root, tag)
    child.text = str(n)

with open('output.xml', 'wb') as outfile:
    doc.write(outfile, 
              xml_declaration=True, 
              encoding='utf-8', 
              pretty_print=True
              ) 
