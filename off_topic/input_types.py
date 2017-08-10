import os
import memento_fetch as mf
from abc import ABCMeta

class InputType:
    
    def __init__(self, input_arguments, logger):
        self.logger = logger
        self.input_arguments = input_arguments

    def get_filelist(self):
        pass

class WARCInput:
    pass

class ArchiveItInput:
    pass

class TimeMapInput:
    pass

class URIListInput:
    pass

class DirInput(InputType):

    def get_filelist(self):

        self.logger.debug("input arguments: {}".format(self.input_arguments))

        input_directory = self.input_arguments[0]

        self.logger.debug("returning contents of {}".format(input_directory))
        return os.listdir(input_directory)


supported_input_types = {
    'warc': WARCInput,
    'archiveit': ArchiveItInput,
    'timemap': TimeMapInput,
    'uris': URIListInput,
    'dir': DirInput
}

def get_input_type(input_type, arguments, logger):
  

    logger.info("using input type matching input type {}".format(input_type))
    logger.debug("input type arguments: {}".format(arguments))

    return supported_input_types[input_type](arguments, logger)
