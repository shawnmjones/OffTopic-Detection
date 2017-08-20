from requests_futures.sessions import FuturesSession
from requests.exceptions import ConnectionError, TooManyRedirects
import hashlib
import os
import csv
import json
import re
from urllib.parse import urlparse
from datetime import datetime
import time

import pprint
pp = pprint.PrettyPrinter(indent=4)

def generate_logger():
    import logging

    logger = logging.getLogger(__name__)
    logger.propagate = False

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = generate_logger()

mementoExpression = re.compile( r"<([^>]*)>;\s?rel=\".*memento.*\";")
mementoDatetimeExpression = re.compile( r"datetime=\"([^\"]*)")
originalResourceExpression = re.compile( r"<([^>]*)>;\s?rel=\"original\"" )

wayback_domain_list = [
    'wayback.archive-it.org'
]

def list_generator(input_list):

    while len(input_list) > 0:
        for item in input_list:
            yield item

def download_uri_list(uri_list, output_directory):

    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    metadata_filename = "{}/metadata.tsv".format(output_directory)

    # what if metadata file already exists?
    # TODO: add option to force download again
    existing_metadata = {}
    if os.path.exists(metadata_filename):
        existing_metadata = parse_metadata_to_dict(output_directory)

    metadata_file = open(metadata_filename, 'a', 1)
    metadata_writer = csv.writer(metadata_file, delimiter='\t', 
        quotechar='"', quoting=csv.QUOTE_ALL)

    with FuturesSession(max_workers=4) as session:
        session = FuturesSession()
        futures = {}
  
        downloaded_uri_list = []

        for uri in uri_list:

            logger.debug("starting download for uri {}".format(uri))
            if uri not in existing_metadata:
                futures[uri] = session.get(uri)
                downloaded_uri_list.append(uri)
            else:
                logger.debug("skipping download of uri {}".format(uri))
  
        working_uri_list = list(downloaded_uri_list)

        for uri in list_generator(working_uri_list):

            logger.debug("checking done-ness of uri {}".format(uri))
            # TODO: implement a timeout, things may get dicey
            if futures[uri].done():
                logger.debug("uri {} is done".format(uri))

                try:
                    response = futures[uri].result()

                    m = hashlib.md5()
                    m.update(uri.encode('utf-8'))

                    fileroot = m.hexdigest()

                    int_dir1 = "{}/{}".format(output_directory, fileroot[0:4])
                    int_dir2 = "{}/{}".format(int_dir1, fileroot[0:8])
                    storage_dir = "{}/{}".format(int_dir2, fileroot[0:16])

                    if not os.path.isdir(storage_dir):
                        os.makedirs(storage_dir)

                    content_destination_file = "{}/{}.dat".format(
                        storage_dir, m.hexdigest())
                    headers_destination_file = "{}/{}.hdr".format(
                        storage_dir, m.hexdigest())

                    metadata_writer.writerow([uri, response.status_code, response.url, 
                        content_destination_file, headers_destination_file])

                    with open(content_destination_file, 'wb') as f:
                        logger.debug("writing content of uri {} to {}".format(
                            uri, content_destination_file))
                        f.write(response.content)

                    # TODO: what if we want all headers for all responses, not just the last?
                    with open(headers_destination_file, 'w') as f:
                        logger.debug("writing headers of uri {} to {}".format(
                            uri, headers_destination_file))

                        # workaround from: https://github.com/requests/requests/issues/1380
                        json.dump(dict(response.headers), f, indent=4)

                    working_uri_list.remove(uri)
                except ConnectionError as e:
                    metadata_writer.writerow([uri, "ERROR", e, None, None])
                    logger.error("Connection Error while downloading URI {},"
                        "error text: {}".format(uri, e))
                    working_uri_list.remove(uri)
                except TooManyRedirects as e:
                    metadata_writer.writerow([uri, "ERROR", e, None, None])
                    logger.error("Too Many Redirects while downloading URI {},"
                        "error text: {}".format(uri, e))
                    working_uri_list.remove(uri)

            time.sleep(1)

    metadata_file.close()

def parse_metadata_to_dict(directory):

    metadata_dict = {}
    metadata_filename = "{}/metadata.tsv".format(directory)

    logger.info("parsing data from metadata file {}".format(metadata_filename))

    with open(metadata_filename) as metadata_file:

        metadata_reader = csv.reader(metadata_file, delimiter='\t', quotechar='"')
    
        for row in metadata_reader:
            uri = row[0] 
            status_code = row[1]
            response_uri = row[2]
            content_filename = row[3]
            headers_filename = row[4]
    
            metadata_dict.setdefault(uri, {})
            metadata_dict[uri]["content_filename"] = content_filename
            metadata_dict[uri]["headers_filename"] = headers_filename
            metadata_dict[uri]["status"] = status_code

    return metadata_dict

def parse_TimeMap_into_dict(filename, convert_raw_mementos=True):

    logger.debug("parsing timemap filename: {}".format(filename))

    tmdict = {}

    with open(filename) as tmfile:
        tmdata = tmfile.read()

        original_resource = re.findall(originalResourceExpression, tmdata)

        try:
            tmdict["original"] = original_resource[0]
        except IndexError:
            logger.error("TimeMap in file {} could not be processed".format(filename))
            return

        memento_entries = re.findall(mementoExpression, tmdata)
        memento_datetime_entries = re.findall(mementoDatetimeExpression, tmdata)

        if len(memento_entries) != len(memento_datetime_entries):
            raise RunTimeError("The number of memento entries does not match the number of memento_datetime entries in TimeMap at {}".format(filename))

        if len(memento_entries) > 0:

            logger.debug(memento_entries)
    
            for i in range(0, len(memento_entries)):
                urim = memento_entries[i]

                if convert_raw_mementos \
                    and urlparse(urim).netloc in wayback_domain_list \
                    and '/timemap/' not in urim:

                    # in case we have a TimeMap that actually lists raw mementos
                    if 'id_/http' not in urim: 
                        urim = urim.replace('/http', 'id_/http')

                dt = datetime.strptime(memento_datetime_entries[i],
                    "%a, %d %b %Y %H:%M:%S GMT")
   
                #fields = entry[0].split(';')
                #urim = fields[0].strip('<').strip('>')
    
                if urim[0:2] == "//":
                    urim = "https:{}".format(urim)

                memento_data = {
                    "uri-m": urim,
                    "memento-datetime": dt
                }
    
                tmdict.setdefault("mementos", []).append(memento_data)

        else:
            tmdict["mementos"] = []

    return tmdict

def parse_downloads_into_structure(top_directory):

    logger.debug("parsing directory {}".format(top_directory))

    timemap_data = {}

    timemaps_dir = "{}/timemaps".format(top_directory)

    mementos_dir = "{}/mementos".format(top_directory)
    memento_metadata = parse_metadata_to_dict(mementos_dir)

    if not os.path.isdir(timemaps_dir):
        # TODO: can we do a memento-only data structure?
        raise NotImplementedError("No TimeMaps downloaded, memento-only functionality not implemented yet")

    else:

        logger.debug("parsing metadata for TimeMap from dir {}".format(timemaps_dir))

        tm_metadata = parse_metadata_to_dict(timemaps_dir)

        logger.debug("TimeMap metadata loaded: {}".format(tm_metadata))

        for timemap in tm_metadata:

            logger.debug("generating structure for TimeMap {}".format(timemap))
        
            if tm_metadata[timemap]['status'] == '200':
                tm_filename = tm_metadata[timemap]['content_filename']
  
                logger.debug("TimeMap filename: {}".format(tm_filename))

                tm_memdata = parse_TimeMap_into_dict(tm_filename)

                logger.debug("tm_metadata: {}".format(tm_metadata))
                logger.debug("tm_memdata: {}".format(tm_memdata))
    
                original = tm_memdata["original"]
        
                mementos = []

                for memento in tm_memdata["mementos"]:

                    logger.debug("memento: {}".format(memento))
                
                    urim = memento['uri-m']

                    # if there was an error in downloading, then there is
                    # no content to be processed so don't include it
                    if memento_metadata[urim]['status'] != 'ERROR':
                
                        memento['content_filename'] = \
                            memento_metadata[urim]['content_filename']
    
                        memento['headers_filename'] = \
                            memento_metadata[urim]['headers_filename']
                    
                        mementos.append(memento)
                
                timemap_data[timemap] = {}
                timemap_data[timemap]["mementos"] = mementos

    logger.debug("timemap_data: {}".format(timemap_data))

    return timemap_data 

def download_mementos(urims, destination_directory):

    memento_dir = "{}/mementos".format(destination_directory)

    if not os.path.isdir(memento_dir):
        os.makedirs(memento_dir)

    download_uri_list(urims, memento_dir)

def download_TimeMaps_and_mementos(urits, destination_directory, depth):

    logger.info("beginning download of Timemaps and associated mementos")
    logger.debug("URI-T list: {}".format(urits))

    if depth > 0:

        timemap_dir = "{}/timemaps".format(destination_directory)

        if not os.path.isdir(timemap_dir):
            os.makedirs(timemap_dir)

        no_mementos_filename = "{}/no_mementos_list.txt".format(timemap_dir)
        no_mementos_file = open(no_mementos_filename, 'w')

        download_uri_list(urits, timemap_dir)

        logger.debug("calling parse_metadata_to_dict")
        metadata = parse_metadata_to_dict(timemap_dir)
        logger.debug("done with call to parse_metadata_to_dict")

        for urit in urits:

            logger.debug("URI-T: {}".format(urit))

            timemap_filename = metadata[urit]["content_filename"]
            tmdict = parse_TimeMap_into_dict(timemap_filename)

            logger.debug("TimeMap Filename: {}".format(timemap_filename))
            logger.debug("tmdict: {}".format(tmdict))

            try:

                urims = []

                for memento_data in tmdict["mementos"]:

                    urim = memento_data["uri-m"]

                    logger.debug("appending urim {}".format(urim))
                    urims.append(urim)

                download_mementos(urims, destination_directory)

            except KeyError:
                no_mementos_file.write("{}\n".format(urit))

            # TODO: if we can get examples of paging TimeMaps, then we can recurse
            # download_TimeMaps_and_mementos([tmdict["next"], tmdict["prev"], 
            #       destination_directory, depth - 1...)

        no_mementos_file.close()

    logger.info("done downloading timemaps and associated mementos from: {}".format(urits))
