import requests
import os

import memento_fetch
from memento_fetch import download_TimeMaps_and_mementos
from bs4 import BeautifulSoup


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

def retrieve_archiveit_accountid(collection_id):

    accountid = -1

    archiveit_collection_uri = "https://archive-it.org/collections/{}".format(collection_id)

    r = requests.get(archiveit_collection_uri)

    if r.status_code == 200:
        
        soup = BeautifulSoup(r.content)

        for link in soup.find_all('a'):
            uri = link.get('href')

            if uri[0:15] == "/organizations/":
                accountid = uri.replace("/organizations/", "")
                break

        return accountid

    else:
        raise Exception("Cannot retrieve Archive-It account ID for collection {}".format(
            collection_id))


def retrieve_archiveit_seeds(collection_id):

    seeds = []

    seed_resource_uri = "https://partner.archive-it.org/api/seed?collection={}&csv_header=Seed+URL&format=csv&show_field=url".format(collection_id)

    r = requests.get(seed_resource_uri)

    for line in r.content.splitlines():
        line = line.decode('utf-8')
        if line != "Seed URL":
            seeds.append(line.strip().strip('"'))

    return seeds

def download_archiveit_collection(collection_id, output_directory, depth):

    memento_fetch.logger = logger

    base_timemap_link_uri = "http://wayback.archive-it.org/{}/timemap/link".format(collection_id)

    collection_directory = "{}/collection/{}".format(output_directory, collection_id)

    if not os.path.isdir(collection_directory):
        os.makedirs(collection_directory)

    metadata_filename = "{}/metadata.tsv".format(collection_directory)

    metadata_file = open(metadata_filename, "w", 1)

    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    seeds = retrieve_archiveit_seeds(collection_id)

    timemap_uris = []

    logger.info("discovered {} seeds".format(len(seeds)))

    for seed in seeds:
        logger.debug("working on seed [{}]".format(seed))
        timemap_uri = "{}/{}".format(base_timemap_link_uri, seed)
        
        logger.debug("building URI-T for seed {}: {}".format(seed, timemap_uri))
        
        timemap_uris.append(timemap_uri)
        metadata_file.write("{}\t{}\n".format(seed, timemap_uri))    

    download_TimeMaps_and_mementos(timemap_uris, collection_directory, depth) 

    metadata_file.close()
