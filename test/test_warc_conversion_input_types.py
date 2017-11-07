import unittest
import os
import sys
import tarfile
import json

from warcio.archiveiterator import ArchiveIterator

sys.path.append("../off_topic")
from memento_fetch import parse_downloads_into_structure
from warc_conversion_input_types import DirInput

working_dir = "/tmp/test_warc_conversion_input_types/working"
test_output_dir = "/tmp/test_warc_conversion_input_types/test_output"
collections_dir = "/tmp/test_warc_conversion_input_types/collections"

class TestWARCConversionInputTypes(unittest.TestCase):


    @classmethod
    def setUpClass(cls):

        if not os.path.exists(collections_dir):
            os.makedirs(collections_dir)

        if not os.path.exists(working_dir):
            os.makedirs(working_dir)

        if not os.path.exists(test_output_dir):
            os.makedirs(test_output_dir)

        # assume that if the directory exists, then it was already
        # decompressed and untarred from a previous run
        if not os.path.exists("{}/391".format(collections_dir)):
            tar = tarfile.open("samplecontent/391.tar.bz2", "r:bz2")
            tar.extractall(collections_dir)
            tar.close()

#    @classmethod
#    def setUpClass(cls):
#
#        # remove temporary directory
#
#        pass

    def convert_filedata_to_urir_structure(self, filedata):

        cfdata = {}

        for urit in filedata:

            urir = urit.replace("http://wayback.archive-it.org/391/timemap/link/", "")

            for urim in filedata[urit]["mementos"]:

                mdt = filedata[urit]["mementos"][urim]["memento-datetime"].strftime(
                    "%a, %d %b %Y %H:%M:%S GMT")

                cfdata.setdefault(urir, {})
                cfdata[urir].setdefault(mdt, {})

                cfdata[urir][mdt]["content_filename"] = \
                    filedata[urit]["mementos"][urim]["content_filename"]

                cfdata[urir][mdt]["headers_filename"] = \
                    filedata[urit]["mementos"][urim]["headers_filename"]

        return cfdata

    def parse_headers_file(filename):

        headers = {}

        with open(filename) as headerfile:

            headerdata = json.lead(headerfile)

            for key in headerdata:

                key = key.lower()

                headers[key] = headerdata[key]

        return headers

    def test_dir_input(self):

        input_dir = "{}/391".format(collections_dir)
        output_dir = "{}/test_dir_input".format(test_output_dir)

        filedata = parse_downloads_into_structure(input_dir)

        cfdata = self.convert_filedata_to_urir_structure(filedata)

        di = DirInput(input_dir)

        print("input_dir: {}".format(input_dir))
        print("working_dir: {}".format(working_dir))
        print("output_dir: {}".format(output_dir))

        di.write_WARCs(working_dir, output_dir)

        for warcfilename in os.listdir(output_dir):

            with open(warcfilename) as stream:

                for record in ArchiveIterator(stream):

                    if record.rec_type == "response":

                        urir = record.rec_headers.get_header("WARC-Target-URI")
                        mdt = record.rec_headers.get_header("WARC-Date")

                        content_filename = cfdata[urir][mdt]["content_filename"]
                        headers_filename = cfdata[urir][mdt]["headers_filename"]

                        # make sure the content matches and the headers match

                        expected_headers = parse_headers_file(headers_filename) 

                        for line in record.http_headers.headers:
                            key = line[0].lower()
                            value = line[1]

                            self.assertEqual(value, expected_headers[key],
                                "Headers do not match for URI-R {} at"
                                    "memento-datetime {} with header key {}".format(
                                    urir, mdt, key))

                        with open(content_filename) as f:
                            expected_entity = f.read()

                        actual_entity = record.raw_stream.read()

                        self.assertEqual(expected_entity, actual_entity,
                            "Entity does not match for URI-R {} at "
                                "memento-datetime {}".format(urir, mdt))
