from requests_futures.sessions import FuturesSession
from requests.exceptions import ConnectionError, TooManyRedirects
import hashlib
import os
import csv
import json
import re
from datetime import datetime

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

#mementoExpression = re.compile( r"(<.*//[A-Za-z0-9.:=/&,%-_ \?]*>;\s?rel=\"(memento|first memento|last memento|first memento last memento|first last memento)\";\s?datetime=\"(Sat|Sun|Mon|Tue|Wed|Thu|Fri), \d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (19|20)\d\d \d\d:\d\d:\d\d GMT\")" )
#mementoExpression = re.compile( r"<(.*//[^>]*)>;\s?rel=\"(memento|first memento|last memento|first memento last memento|first last memento)\";")
#mementoExpression = re.compile( r"<([^>]*)>;\s?rel=\"(memento|first memento|last memento|first memento last memento|first last memento)\";")
mementoExpression = re.compile( r"<([^>]*)>;\s?rel=\".*memento.*\";")
mementoDatetimeExpression = re.compile( r"datetime=\"([^\"]*)")
#originalResourceExpression = re.compile( r"<(.*//[A-Za-z0-9.:=/&,%-_ \?]*)>;\s?rel=\"original\"" )
originalResourceExpression = re.compile( r"<(.*//[^>]*)>;\s?rel=\"original\"" )


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
                    working_uri_list.remove(uri)
                except TooManyRedirects as e:
                    metadata_writer.writerow([uri, "ERROR", e, None, None])
                    working_uri_list.remove(uri)

    metadata_file.close()

def parse_metadata_to_dict(directory):

    metadata_dict = {}
    metadata_filename = "{}/metadata.tsv".format(directory)
    metadata_file = open(metadata_filename)

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
    
    metadata_file.close()

    return metadata_dict

def parse_TimeMap_into_dict(filename):

    logger.debug("parsing timemap filename: {}".format(filename))

    tmdict = {}

    with open(filename) as tmfile:
        tmdata = tmfile.read()

        original_resource = re.findall(originalResourceExpression, tmdata)

        try:
            tmdict["original"] = original_resource[0]
        except IndexError:
            print(filename)
            return

        memento_entries = re.findall(mementoExpression, tmdata)
        memento_datetime_entries = re.findall(mementoDatetimeExpression, tmdata)

        if len(memento_entries) != len(memento_datetime_entries):
            raise RunTimeError("The number of memento entries does not match the number of memento_datetime entries in TimeMap at {}".format(filename))

        if len(memento_entries) > 0:

            logger.debug(memento_entries)
    
            for i in range(0, len(memento_entries)):
                urim = memento_entries[i]
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

    logger.info("parsing directory {}".format(top_directory))

    timemap_data = {}

    timemaps_dir = "{}/timemaps".format(top_directory)

    mementos_dir = "{}/mementos".format(top_directory)
    mementos_metadata_filename = "{}/metadata.tsv".format(mementos_dir)
    memento_metadata = parse_metadata_to_dict(mementos_dir)

    if not os.path.isdir(timemaps_dir):
        # TODO: can we do a memento-only data structure?
        raise NotImplementedError("No TimeMaps downloaded, memento-only functionality not implemented yet")

    else:

        timemaps_metadata_filename = "{}/metadata.tsv".format(timemaps_dir)
        tm_metadata = parse_metadata_to_dict(timemaps_dir)

        logger.info("using timemaps metadata file {}".format(
            timemaps_metadata_filename))

        for timemap in tm_metadata:
        
            if tm_metadata[timemap]['status'] == '200':
                tm_filename = tm_metadata[timemap]['content_filename']
  
                logger.debug("TimeMap filename: {}".format(tm_filename))

                tm_memdata = parse_TimeMap_into_dict(tm_filename)

                #logger.info("tm_metadata: {}".format(tm_metadata))
    
                original = tm_memdata["original"]
        
                mementos = []

                for memento in tm_memdata["mementos"]:
                    logger.debug("memento: {}".format(memento))
                
                    urim = memento['uri-m']
                    #dt = memento['memento-datetime']
                
                    memento['content_filename'] = \
                        memento_metadata[urim]['content_filename']
                
                    mementos.append(memento)
                
                timemap_data[timemap] = {}
                timemap_data[timemap]["mementos"] = mementos

    return timemap_data 

def download_mementos(urims, destination_directory):

    memento_dir = "{}/mementos".format(destination_directory)

    if not os.path.isdir(memento_dir):
        os.makedirs(memento_dir)

    download_uri_list(urims, memento_dir)

def download_TimeMaps_and_mementos(urits, destination_directory, depth):

    if depth > 0:

        timemap_dir = "{}/timemaps".format(destination_directory)

        if not os.path.isdir(timemap_dir):
            os.makedirs(timemap_dir)

        no_mementos_filename = "{}/no_mementos_list.txt".format(timemap_dir)
        no_mementos_file = open(no_mementos_filename, 'w')

        download_uri_list(urits, timemap_dir)
        metadata = parse_metadata_to_dict(timemap_dir)

        for urit in urits:

            timemap_filename = metadata[urit]["content_filename"]
            tmdict = parse_TimeMap_into_dict(timemap_filename)

            logger.debug("URI-T: {}".format(urit))
            logger.debug("TimeMap Filename: {}".format(timemap_filename))
            logger.debug("tmdict: {}".format(tmdict))

            try:

                urims = []

                for memento_data in tmdict["mementos"]:
                    urims.append(memento_data["uri-m"])

                download_mementos(urims, destination_directory)

            except KeyError:
                no_mementos_file.write("{}\n".format(urit))

            # TODO: if we can get examples of paging TimeMaps, then we can recurse
            # download_TimeMaps_and_mementos([tmdict["next"], tmdict["prev"], 
            #       destination_directory, depth - 1...)

        no_mementos_file.close()
