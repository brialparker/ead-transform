import logging
import lxml.etree as ET
import re

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
                # check whether a box container exists already; if so, break out
                for c in did.iterchildren(tag='container'):
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


    #======================================
    # Missing extents in physdesc elements
    #======================================
    def add_missing_extents(self):
        for physdesc in self.tree.findall('.//physdesc'):
            children = physdesc.getchildren()
            if not children:
                ext = ET.SubElement(physdesc, "extent")
                ext.text = physdesc.text
                physdesc.text = ''
                self.logger.info(
                    '{0} : Added missing extent element to {1}'.format(
                        self.name, physdesc
                        ))


    #===========================
    # fix incorrect box numbers
    #===========================
    def fix_box_number_discrepancies(self):
        boxes = [c for c in self.tree.iter(
                    'container') if c.get('type') == 'box'
                    ]
                    
        for box in boxes:
            match = re.search(r'^(box)?(\d+).\d+$', box.get('id'))
            if box.text != match.group(2):
                box.text = match.group(2)
                self.logger.info(
                    '{0} : Corrected box {1} to {2}'.format(
                        self.name, ET.tostring(box), match.group(2)
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

    ''' This method is in progress; should move each scope and content note to 
        the corresponding position in the in-depth section.
    
    #==============================================================
    # Move scope and content notes from analytic cover to in-depth
    #==============================================================
    def move_scopecontent(self):
        scope = self.tree.findall(
            'dsc[@type="analyticover"]/scopecontent'
            )
        print(scope)
        # iterate over scope and content notes inside analytic cover section
        if scope:
            for sc in scope:
                print(sc)
                paragraphs = [node for node in sc if node.tag is 'p']
                if not all([p.text is None for p in paragraphs]):
                    # move the content over
                    parent = scope.getparent()
                    indepth = parent.find('dsc[@type="in-depth"]')
                    indepth.text = ac.text
                # otherwise, and finally, remove (all para. are empty)
                ac.getparent().remove(ac) '''

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

