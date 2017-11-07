import logging
import os
import json

from datetime import datetime

from abc import ABCMeta, abstractmethod

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from memento_fetch import parse_downloads_into_structure

def ensure_dir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)

class InputType(metaclass=ABCMeta):

    def __init__(self, input_arguments):

        logger = logging.getLogger(__name__)
        logger.debug("Generating an input type class")

        self.input_arguments = input_arguments

    @abstractmethod
    def write_WARCs(self, working_directory, output_directory):
        pass

class ArchiveItInput(InputType):

    def __init__(self, input_arguments):
        raise NotImplementedError("{} not yet implemented".format(type(self).__name__))

class TimeMapInput(InputType):

    def __init__(self, input_arguments):
        raise NotImplementedError("{} not yet implemented".format(type(self).__name__))

class DirInput(InputType):

#    def __init__(self, input_arguments):
#        raise NotImplementedError("{} not yet implemented".format(type(self).__name__))

    def write_WARCs(self, working_directory, output_directory):

        logger = logging.getLogger(__name__)

        input_directory = self.input_arguments

        ensure_dir(working_directory)
        ensure_dir(output_directory)

        logger.info("using input directory of {}".format(input_directory))
        print("using input directory of {}".format(input_directory))

        filedata = parse_downloads_into_structure(input_directory)

        collectionid = os.path.basename(input_directory)

        warccounter = 0

        for urit in filedata:

            warccounter += 1
            now = datetime.now().strftime("%Y%m%D%H%M%S")

            warcfilename = "{}/ARCHIVEIT-{}-{}.warc.gz".format(
                output_directory, collectionid, warccounter, now)

            with open(warcfilename, 'wb') as output:

                writer = WARCWriter(output, gzip=True)

                for urim in filedata[urit]["mementos"]:
    
                    urir = urim[urim.find("/http") + 1:] 
                    content_filename = filedata[urit]["mementos"][urim]["content_filename"]
                    headers_filename = filedata[urit]["mementos"][urim]["headers_filename"]

                    if headers_filename[0] != '/':
                        headers_filename = "{}/{}".format(input_directory, headers_filename)

                    with open(headers_filename) as f:
                        header_dict = json.load(f)

                    if content_filename[0] != '/':
                        content_filename = "{}/{}".format(input_directory, content_filename)


                    logger.debug("headers: {}".format(header_dict))
                    print("headers: {}".format(header_dict))
                    print("headers: {}".format(header_dict.items()))

                    http_headers = StatusAndHeaders(
                        '200 OK', header_dict.items(), protocol='HTTP/1.1')

                    with open(content_filename, encoding='utf-8') as content:
                        record = writer.create_warc_record('http://example.com/', 'response',
                                            payload=content,
                                            http_headers=http_headers)

                    writer.write_record(record)


            
        

supported_input_types = {
    'archiveit': ArchiveItInput,
    'timemap': TimeMapInput,
    'dir': DirInput
}
