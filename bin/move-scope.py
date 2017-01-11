#!/usr/bin/env python3

import lxml.etree as ET
import sys

xmlfile = sys.argv[1]
outfile = '/Users/westgard/Desktop/output.xml'

class Ead(object):
    
    def __init__(self, xml):
        parser = ET.XMLParser(remove_blank_text=True)
        self.tree = ET.parse(xmlfile, parser)
        self.root = self.tree.getroot()

    def move_scopecontent(self):
        analyticover = self.tree.find('.//dsc[@type="analyticover"]')
        indepth = self.tree.find('.//dsc[@type="in-depth"]')
        
        if analyticover is not None:
            # locate all the scope and content elems in the analytic cover
            all_scopes = analyticover.findall('.//scopecontent')
            for scope in all_scopes:
                parent = scope.getparent()
                id = parent.attrib['id'].rstrip('.a')
                # move the scope and content notes over to corresponding elem
                path = ".//{0}[@id='{1}']".format(parent.tag, id)
                indepth.find(path).insert(0, scope)
                # delete hte analytic cover element
                analyticover.getparent().remove(analyticover) 


e = Ead(xmlfile)
e.move_scopecontent()
e.tree.write(outfile, pretty_print=True)

