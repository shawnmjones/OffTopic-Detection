import os
import memento_fetch
from memento_fetch import download_TimeMaps_and_mementos, parse_downloads_into_structure, download_uri_list, parse_metadata_to_dict
from abc import ABCMeta, abstractmethod
from warcio.archiveiterator import ArchiveIterator
import csv
import random
from datetime import datetime
import hashlib
import json

import archiveit_utils
from archiveit_utils import download_archiveit_collection

class InputType(metaclass=ABCMeta):

    def __init__(self, input_arguments, output_directory, logger):
        self.logger = logger
        self.input_arguments = input_arguments
        self.output_directory = output_directory
        self.filedata = None

    @abstractmethod
    def get_filedata(self):
        pass

class WARCInput(InputType):

    def get_filedata(self):

        timemap_data = {}

        memento_fetch.logger = self.logger

        warcfiles = self.input_arguments

        collection_directory = "{}/collection/warc{}".format(
                self.output_directory, random.randint(0, 9999))

        self.logger.info("storing collection in {}".format(
            collection_directory))

        memento_directory = "{}/mementos".format(collection_directory)
        metadata_filename = "{}/metadata.tsv".format(memento_directory)

        if not os.path.isdir(memento_directory):
            os.makedirs(memento_directory)

        metadata_file = open(metadata_filename, 'a', 1)
        metadata_writer = csv.writer(metadata_file, delimiter='\t', 
            quotechar='"', quoting=csv.QUOTE_ALL)

        timemaps = {}

        for warcfile in warcfiles:
            
            with open(warcfile, 'rb') as stream:

                for record in ArchiveIterator(stream):

                    if record.rec_type == 'response':
                        urir = record.rec_headers.get_header('WARC-Target-URI')

                        # WARCs keep track of DNS requests
                        if urir.split(':')[0] != 'dns':

                            self.logger.debug("URI: {}".format(urir))
    
                            # for TimeMaps
                            memento_datetime = datetime.strptime(
                                record.rec_headers.get_header('WARC-Date'),
                                '%Y-%m-%dT%H:%M:%SZ'
                                )
    
                            self.logger.debug("Memento-Datetime: {}".format(
                                memento_datetime))
    
                            headers = {}
    
                            for line in record.http_headers.headers:
                                key = line[0]
                                value = line[1]
    
                                headers[key] = value
    
                            self.logger.debug("Headers: {}".format(headers))
    
                            file_content = record.raw_stream.read()

                            urim = "local-archive:{}/{}".format(
                                memento_datetime.strftime('%Y%M%d%H%M%S'), urir)

                            timemaps[urir] = {}
                            timemaps[urir].setdefault("mementos", []).append( {
                                "uri-m": urim,
                                "memento-datetime": memento_datetime
                            } )
    
                            m = hashlib.md5()
                            m.update(urim.encode('utf-8'))

                            fileroot = m.hexdigest()

                            int_dir1 = "{}/{}".format(
                                memento_directory, fileroot[0:4])

                            int_dir2 = "{}/{}".format(int_dir1, fileroot[0:8])
                            storage_dir = "{}/{}".format(int_dir2, fileroot[0:16])

                            if not os.path.isdir(storage_dir):
                                os.makedirs(storage_dir)

                            content_destination_file = "{}/{}.dat".format(
                                storage_dir, m.hexdigest())

                            headers_destination_file = "{}/{}.hdr".format(
                                storage_dir, m.hexdigest())
                  
                            status_code = record.http_headers.get_statuscode()

                            metadata_writer.writerow([urim, status_code, urir,
                                content_destination_file,
                                headers_destination_file])

                            with open(content_destination_file, 'wb') as f:
                                self.logger.debug("writing content of uri {} to {}"
                                    .format(urir, content_destination_file))
                                f.write(file_content)

                            with open(headers_destination_file, 'w') as f:
                                self.logger.debug("writing headers of uri {} to {}"
                                    .format(urir, headers_destination_file))
                                json.dump(dict(headers), f, indent=4)

        metadata_file.close()

        timemap_directory = "{}/timemaps".format(collection_directory)
        metadata_filename = "{}/metadata.tsv".format(timemap_directory)

        if not os.path.isdir(timemap_directory):
            os.makedirs(timemap_directory)

        metadata_file = open(metadata_filename, 'a', 1)
        metadata_writer = csv.writer(metadata_file, delimiter='\t', 
            quotechar='"', quoting=csv.QUOTE_ALL)

        for urir in timemaps:
            urit = "local-archive:timemap/{}".format(urir)

            m = hashlib.md5()
            m.update(urit.encode('utf-8'))

            # sort mementos
            mementos = []
            for memento in timemaps[urir]["mementos"]:
                urim = memento['uri-m']
                mdt = memento['memento-datetime']

                mementos.append( (mdt, urim) )

            mementos.sort()

            from_date = mementos[0][0].strftime("%a, %d %b %Y %H:%M:%S GMT")
            until_date = mementos[-1][0].strftime("%a, %d %b %Y %H:%M:%S GMT")

            timemap_string = '<{}>; rel="original",\n'.format(urir)
            timemap_string += '<{}>; rel="self"; ' \
                'type="application/link-format"; ' \
                'from="{}"; until="{}",\n'.format(urit, from_date, until_date)

            memento_entries = []

            for i in range(len(mementos)):

                if i == 0 and i == len(mementos) - 1:
                    rel = "first last memento"

                elif i == 0:
                    rel = "first memento"

                elif i == len(mementos) - 1:
                    rel = "last memento"

                else:
                    rel = "memento"

                memento_datetime = mementos[i][0]
                self.logger.debug("building timemap with memento_datetime: {}"
                    .format(memento_datetime))
                urim = mementos[i][1]

                memento_entries.append('<{}>; rel="{}"; datetime="{}"'.format(
                    urim, rel, memento_datetime.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                        )
                    ))

            timemap_string += ',\n'.join(memento_entries)

            fileroot = m.hexdigest()
            
            int_dir1 = "{}/{}".format(
                timemap_directory, fileroot[0:4])
            
            int_dir2 = "{}/{}".format(int_dir1, fileroot[0:8])
            storage_dir = "{}/{}".format(int_dir2, fileroot[0:16])
            
            if not os.path.isdir(storage_dir):
                os.makedirs(storage_dir)

            timemap_file = "{}/{}.dat".format(
                storage_dir, m.hexdigest())

            self.logger.debug("writing timemap to {}".format(timemap_file))

            with open(timemap_file, 'w') as f:
                f.write(timemap_string)

            metadata_writer.writerow([urit, "200", urit, timemap_file, None])

        metadata_file.close()

        self.logger.info("parsing downloads into structure from {}".format(
            collection_directory))

        timemap_data = parse_downloads_into_structure(collection_directory)

        self.logger.info("returning data about collection created from WARC")

        return timemap_data
                    

InputType.register(WARCInput)

class ArchiveItInput(InputType):

    def get_filedata(self):

        archiveit_utils.logger = self.logger

        if self.filedata == None:

            if str(self.input_arguments[0])[0:4] == 'http':
                collection_id = self.input_arguments[0].replace(
                    "https://archive-it.org/collections/", '').strip('/')
            else:
                collection_id = self.input_arguments[0]
    
            download_archiveit_collection(collection_id, self.output_directory, 1)

            # TODO: input_types requires too much knowledge of memnto_fetch
            collection_directory = "{}/collection/{}".format(
                self.output_directory, collection_id)
    
            timemap_data = parse_downloads_into_structure(collection_directory)

            self.filedata = timemap_data
        else:
            timemap_data = self.filedata

        return timemap_data

InputType.register(ArchiveItInput)

class TimeMapInput(InputType):

    def get_filedata(self):

        urits = self.input_arguments
        filelist = []

        self.logger.debug("attempting to download files for URI-T: {}"
            .format(urits))

        download_TimeMaps_and_mementos(urits, self.output_directory, 1)

        timemap_data = parse_downloads_into_structure(self.output_directory)

        return timemap_data

InputType.register(TimeMapInput)

class URIListInput(InputType):

    def __init__(self, input_arguments, output_directory, logger):
        raise NotImplementedError("Simple URI list inputs not available yet!")


    def get_filedata(self):
        pass
            

InputType.register(URIListInput)

class DirInput(InputType):

    def get_filedata(self):

        input_directory = self.input_arguments[0]

        return parse_downloads_into_structure(input_directory)

InputType.register(DirInput)

supported_input_types = {
    'warc': WARCInput,
    'archiveit': ArchiveItInput,
    'timemap': TimeMapInput,
    'dir': DirInput
}

def get_input_type(input_type, arguments, directory, logger):

    logger.info("using input type {}".format(input_type))
    logger.debug("input type arguments: {}".format(arguments))
    logger.debug("using supported input type {}".format(
        supported_input_types[input_type]))

    return supported_input_types[input_type](arguments, directory, logger)
