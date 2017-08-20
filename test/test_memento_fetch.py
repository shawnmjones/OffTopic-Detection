import unittest
import sys
import os
import shutil
import logging
import pprint

sys.path.append('../off_topic')
import memento_fetch as mf

logging.basicConfig(level=logging.DEBUG)

# this is useful for debugging at times
pp = pprint.PrettyPrinter(indent=4)

working_dir = '/tmp/test_memento_fetch'

class TestParseDownloadsIntoStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        logger = logging.getLogger(__name__)
        mf.logger = logger

        if not os.path.isdir(working_dir):
            os.makedirs(working_dir)

        # in case we have something leftover from a previous run
        if os.path.isdir('{}/samplecontent'.format(working_dir)):
            shutil.rmtree(working_dir)
        
        shutil.copytree('samplecontent', "{}/samplecontent".format(working_dir))

    @classmethod
    def tearDownClass(cls):

        shutil.rmtree(working_dir)

    def test_key_error(self):

        os.makedirs("{}/mementos".format(working_dir))
        os.makedirs("{}/timemaps".format(working_dir))

        shutil.copy("{}/samplecontent/metadata_with_error_memento.tsv"
            .format(working_dir), 
            "{}/mementos/metadata.tsv".format(working_dir))

        shutil.copy("{}/samplecontent/metadata_with_error_timemap.tsv"
            .format(working_dir), 
            "{}/timemaps/metadata.tsv".format(working_dir))

        shutil.copy("{}/samplecontent/20.dat".format(working_dir),
            "{}/timemaps/20.dat".format(working_dir))

        with open("{}/timemaps/metadata.tsv".format(working_dir)) as f:
            tmdata = f.read()

        tmdata = tmdata.replace('${working_dir}', working_dir)

        with open("{}/timemaps/metadata.tsv".format(working_dir), 'w') as f:
            f.write(tmdata)

        datadict = mf.parse_downloads_into_structure(working_dir)

        pp.pprint(datadict)

        self.assertEqual(len(datadict['local-archive:timemap/20']['mementos']), 0)

        shutil.rmtree("{}/mementos".format(working_dir))
        shutil.rmtree("{}/timemaps".format(working_dir))
