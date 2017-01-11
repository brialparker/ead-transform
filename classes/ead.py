import logging
import lxml.etree as ET
import re
import string

class Ead(object):

    '''Encoded Archival Description object'''

    def __init__(self, id, handle, xmlfile):
        self.name = id
        parser = ET.XMLParser(remove_blank_text=True)
        self.tree = ET.parse(xmlfile, parser)
        self.handle = handle
        self.root = self.tree.getroot()
        self.logger = logging.getLogger("transform.transform")
        self.logger.info('********** Transforming {0} **********'.format(
            self.name
            ).upper()) 


    #=============================
    # Add title attribute to dao
    #=============================
    def add_title_to_dao(self):
        for dao in self.tree.findall('.//dao'):
            parent = dao.getparent()
            unittitle = parent.find('unittitle').text
            if unittitle:
                dao.set('title', unittitle)
                self.logger.info(
                    'Added title "{0}" to dao element'.format(unittitle)
                    )
            else:
                self.logger.warn('Cannot find unittitle for dao element')


    #=================================================
    # Add handle uri as an attribute of the eadid elem
    #=================================================
    def insert_handle(self):
        eadid = self.tree.find('.//eadid')
        if eadid is not None:
            eadid.set('url', self.handle)
            self.logger.info('{0} : Added handle to eadid => "{1}"'.format(
                        self.name, self.handle
                        ))


    #=================================
    # Add box containers where absent
    #=================================
    def add_missing_box_containers(self):
        # iterate over item- and file-level containers
        for n, did in enumerate(self.tree.iter('did')):
            parent = did.getparent()
            parent_level = parent.get('level')

            if parent_level in ['file', 'item']:
                # iterate over all the container nodes
                for c in did.iterchildren(tag='container'):
                
                    # remove "box" from the id attribute
                    if c.get('id'):
                        old_id = c.get('id')
                        c.set('id', old_id.lstrip('box'))
                        self.logger.info(
                            '{0} : Removed "box" prefix from id {1}'.format(
                                self.name, old_id 
                                ))
                    
                    # remove "box" from the parent attribute
                    if c.get('parent'):
                        old_parent = c.get('parent')
                        c.set('parent', old_parent.lstrip('box'))
                        self.logger.info(
                            '{0} : Removed "box" prefix from parent {1}'.format(
                                self.name, old_parent
                                ))
                    
                    # check whether box container exists; & if so, break out            
                    if c.get('type') == 'box':
                        break
                    
                    # if not, create a box container
                    else:
                        box_attribute = c.get('parent') or ''
                        match = re.search(r'^(box)?(\d+).(\d+)$', box_attribute)
                        
                        # create attributes corresponding to the parent box
                        if match:
                            box_number = match.group(2)
                            box_id = "{0}.{1}".format(match.group(2),
                                                      match.group(3)
                                                      )
                            new_container = ET.SubElement(did, "container")
                            new_container.set('type', 'box')
                            new_container.set('id', box_id)
                            new_container.text = box_number
                            self.logger.info(
                                '{0} : Added box {1} to did "{2}"'.format(
                                    self.name, box_id, box_attribute
                                    ))


    #================================
    # Sort containers hierarchically
    #================================
    def sort_containers(self):
        # iterate over item- and file-level containers
        for n, did in enumerate(self.tree.iter('did')):
            for elem in list(did):
                if 'parent' in elem.keys():
                    did.append(elem)
                    self.logger.info(
                    '{0} : Moving child container to last position'.format(
                        self.name
                        ))


    #======================================
    # Missing extents in physdesc elements
    #======================================
    def add_missing_extents(self):
        paths = ['./archdesc/did/physdesc', './archdesc/dsc/c01/did/physdesc']
        for path in paths:
            for physdesc in self.tree.findall(path):
                children = physdesc.getchildren()
                if not children:
                    ext = ET.SubElement(physdesc, "extent")
                    ext.text = physdesc.text
                    physdesc.text = ''
                    self.logger.info(
                        '{0} : Added missing extent element to {1}'.format(
                            self.name, physdesc
                            ))


    #======================================
    # Clean up and standardize extent text
    #======================================
    def correct_text_in_extents(self):
        for extent in self.tree.findall('.//extent'):
            # split text into words and filter word approximately
            words = [w for w in extent.text.split() if w != 'approximately']
            numeric_chars = set('0123456789,')
            for word in words:
                # remove line breaks and trailing spaces
                word = word.replace("\n", "")
                word = word.rstrip()
                # check word is digits/commas only and remove comma unless last
                if all([(c in numeric_chars) for c in word]):
                    word = word[:-1].replace(",", "") + word[-1:]
                # change linear and feet into standard forms
                if word == 'Linear' or word == 'lin':
                    word = 'linear'
                elif word == 'ft':
                    word = 'feet'
            # re-join the words
            result = ' '.join(words)
            if result != extent.text:
                print('Changed {0} to {1}'.format(extent.text, result))
                self.logger.info(
                    '{0} : Corrected extent from {0} to {1}'.format(
                        extent.text, result
                        ))
                extent.text = result


    #===========================
    # fix incorrect box numbers
    #===========================
    def fix_box_number_discrepancies(self):
        # find all the box-level containers
        boxes = [c for c in self.tree.iter(
                    'container') if c.get('type') == 'box'
                    ]
        # iterate over these containers
        for box in boxes:
            # remove the "box" prefix from the ID
            current_id = box.get('id')
            new_id = current_id.lstrip('box')
            if current_id != new_id:
                box.set('id', new_id)
                self.logger.info(
                    '{0} : Changed box "{1}" to "{2}"'.format(
                        self.name, current_id, new_id
                        ))
            # make the text of element match the id attribute        
            match = re.search(r'^(box)?(\d+).\d+$', box.get('id'))
            current_text = box.text
            new_text = match.group(2)
            if current_text != new_text:
                box.text = new_text
                self.logger.info(
                    '{0} : Corrected box {1} to {2}'.format(
                        self.name, current_text, box.text
                        ))


    #==================================================
    # Remove elements containing only empty paragraphs
    #==================================================
    def remove_empty_elements(self):
        node_types = ['bioghist', 'processinfo', 'scopecontent']
        
        # check for each of the three elements above
        for node_type in node_types:
            # iterate over instances of the element
            for node in self.tree.findall('.//' + node_type):
                parent = node.getparent()
                if node.text is not None:
                    break
                # find all the paragraphs in the node
                paragraphs = node.findall('p')
                # if any contain text, break the loop
                for p in paragraphs:
                    if len(p) > 0 or p.text is not None:
                        break
                # otherwise remove the parent element
                parent.remove(node)
                self.logger.info(
                    "{0} : Removed empty element {1}".format(
                        self.name, node_type
                        ))


    #==============================
    # Remove "Guide to" from title
    #==============================
    def remove_opening_of_title(self):
        titleproper = self.tree.find('.//titleproper')
        
        # if title.text begins with "Guide to", remove it & capitalize
        if titleproper is not None and titleproper.text is not None:
            titleproper_old = titleproper.text

            if titleproper_old.startswith("Guide to"):
                titleproper_new = titleproper_old[9].upper() + \
                    titleproper_old[10:]
                titleproper.text = titleproper_new

                if len(titleproper_new) > 25:
                    abbrev_new = titleproper_new[:25] + "..."
                    abbrev_old = titleproper_old[:25] + "..."
                else:
                    abbrev_new = titleproper_new
                    abbrev_old = titleproper_old
        
                self.logger.info(
                    '{0} : Removed "Guide to" from title => "{1}"'.format(
                        self.name, titleproper_new
                        ))
                print("  Changed title: {0} => {1}".format(abbrev_old, 
                                                           abbrev_new
                                                           ))


    #==============================================================
    # Move scope and content notes from analytic cover to in-depth
    #==============================================================
    def move_scopecontent(self):
        analyticover = self.tree.find('.//dsc[@type="analyticover"]')
        indepth = self.tree.find('.//dsc[@type="in-depth"]')
        
        if analyticover is not None and indepth is not None:
            # locate all the scope and content elems in the analytic cover
            all_scopes = analyticover.findall('.//scopecontent')

            for scope in all_scopes:
                parent = scope.getparent()
                id = parent.attrib['id'].rstrip('.a')

                # move the scope and content notes over to corresponding elem
                path = ".//{0}[@id='{1}']".format(parent.tag, id)
                destination = indepth.find(path)
                
                if destination is not None:
                    destination.insert(0, scope)
                    self.logger.info(
                        '{0} : Moved "scopecontent" elem from analytic '
                        'to in-depth sections'.format(self.name)
                        )
                else:
                    print("cannot find destination path")
                    
            # delete the analytic cover element
            analyticover.getparent().remove(analyticover)
            self.logger.info(
                        '{0} : Deleted analyticover element'.format(self.name)
                        )


    #==================================================
    # Remove alternative abstracts used for ArchivesUM
    #==================================================
    def remove_multiple_abstracts(self):
        abstracts = [a for a in self.root.iter('abstract')]
        print("  Found {0} abstracts:".format(len(abstracts)))

        if len(abstracts) > 1:
            for abstract_num, abstract in enumerate(abstracts):
                label = abstract.get('label')
                if label == "Short Description of Collection":
                    print("    {0}. Keeping Short Description".format(
                                                        abstract_num +1)
                                                        )
                else:
                    print("    {0}. Removing abstract '{1}'...".format(
                        abstract_num + 1, label)
                        )
                    abstract.getparent().remove(abstract)
                    self.logger.info(
                        "{0} : removing additional abstracts".format(self.name))
        else:
            print("  There is only one abstract.")

