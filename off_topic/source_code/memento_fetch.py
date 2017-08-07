from requests_futures.sessions import FuturesSession
from requests.exceptions import ConnectionError
import hashlib
import os
import csv
import json
import re

# TODO: come up with a logging plan
import logging

mementoExpression = re.compile( r"(<.*//[A-Za-z0-9.:=/&,%-_ \?]*>;\s?rel=\"(memento|first memento|last memento|first memento last memento|first last memento)\";\s?datetime=\"(Sat|Sun|Mon|Tue|Wed|Thu|Fri), \d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (19|20)\d\d \d\d:\d\d:\d\d GMT\")" )

def list_generator(input_list):

    while len(input_list) > 0:
        for item in input_list:
            yield item

def download_uri_list(uri_list, output_directory):

    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    metadata_filename = "{}/metadata.tsv".format(output_directory)

    # TODO: what if metadata file already exists?

    metadata_file = open(metadata_filename, 'w', 1)
    metadata_writer = csv.writer(metadata_file, delimiter='\t', 
        quotechar='"', quoting=csv.QUOTE_ALL)

    with FuturesSession(max_workers=4) as session:
        session = FuturesSession()
        futures = {}
    
        for uri in uri_list:
            logging.info("starting download for uri {}".format(uri))
            futures[uri] = session.get(uri)
  
        working_uri_list = list(uri_list)

        for uri in list_generator(working_uri_list):

            logging.debug("checking done-ness of uri {}".format(uri))
            # TODO: implement a timeout, things may get dicey
            if futures[uri].done():
                logging.debug("uri {} is done".format(uri))

                try:
                    response = futures[uri].result()

                    m = hashlib.md5()
                    m.update(uri)

                    fileroot = m.hexdigest()

                    int_dir1 = "{}/{}".format(output_directory, fileroot[0:4])
                    int_dir2 = "{}/{}".format(int_dir1, fileroot[0:8])
                    storage_dir = "{}/{}".format(int_dir2, fileroot[0:16])

                    if not os.path.isdir(storage_dir):
                        os.makedirs(storage_dir)

                    content_destination_file = "{}/{}.dat".format(storage_dir, m.hexdigest())
                    headers_destination_file = "{}/{}.hdr".format(storage_dir, m.hexdigest())

                    metadata_writer.writerow([uri, response.status_code, response.url, 
                        content_destination_file, headers_destination_file])

                    with open(content_destination_file, 'w') as f:
                        logging.info("writing content of uri {} to {}".format(uri, content_destination_file))
                        f.write(response.content)

                    # TODO: what if we want all headers for all responses, not just the last?
                    with open(headers_destination_file, 'w') as f:
                        logging.info("writing headers of uri {} to {}".format(uri, headers_destination_file))

                        # workaround from: https://github.com/requests/requests/issues/1380
                        json.dump(dict(response.headers), f, indent=4)

                    working_uri_list.remove(uri)
                except ConnectionError as e:
                    metadata_writer.writerow([uri, "ERROR", e.message, None, None])
                    working_uri_list.remove(uri)

    metadata_file.close()

def download_metadata_to_dict(directory):
 
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

def parseTimeMapIntoDict(filename):

    tmdict = {}

    with open(filename) as tmfile:
        tmdata = tmfile.read()
        memento_entries = re.findall(mementoExpression, tmdata)

        logging.debug(memento_entries)

        for entry in memento_entries:
            fields = entry[0].split(';')
            urim = fields[0].strip('<').strip('>')

            if urim[0:2] == "//":
                urim = "https:{}".format(urim)

            tmdict.setdefault("mementos", []).append(urim)

    return tmdict

def download_TimeMaps_and_mementos(urits, destination_directory, depth):

    if depth > 0:

        timemap_dir = "{}/timemaps".format(destination_directory)
        memento_dir = "{}/mementos".format(destination_directory)

        if not os.path.isdir(timemap_dir):
            os.makedirs(timemap_dir)

        if not os.path.isdir(memento_dir):
            os.makedirs(memento_dir)

        no_mementos_filename = "{}/no_mementos_list.txt".format(timemap_dir)
        no_mementos_file = open(no_mementos_filename, 'w')

        download_uri_list(urits, timemap_dir)
        metadata = download_metadata_to_dict(timemap_dir)

        for urit in urits:

            timemap_filename = metadata[urit]["content_filename"]
            tmdict = parseTimeMapIntoDict(timemap_filename)

            try:
                download_uri_list(tmdict["mementos"], memento_dir)
            except KeyError:
                no_mementos_file.write("{}\n".format(urit))

            # TODO: if we can get examples of paging TimeMaps, then we can recurse
            # download_TimeMaps_and_mementos([tmdict["next"], tmdict["prev"], 
            #       destination_directory, depth - 1...)

        no_mementos_file.close()
