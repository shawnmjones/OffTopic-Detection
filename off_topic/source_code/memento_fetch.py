from requests_futures.sessions import FuturesSession
from requests.exceptions import ConnectionError
import hashlib
import os
import csv
import json

# TODO: come up with a logging plan
import logging

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
                    content_destination_file = "{}/{}.dat".format(output_directory, m.hexdigest())
                    headers_destination_file = "{}/{}.hdr".format(output_directory, m.hexdigest())

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
