import requests
import os
from memento_fetch import download_TimeMaps_and_mementos
from bs4 import BeautifulSoup

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
        if line != "Seed URL":
            seeds.append(line.strip())

    return seeds

def download_archiveit_collection(collection_id, output_directory, depth):
  
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

    for seed in seeds:
        timemap_uri = "{}/{}".format(base_timemap_link_uri, seed)
        timemap_uris.append(timemap_uri)
        metadata_file.write("{}\t{}\n".format(seed, timemap_uri))    

    download_TimeMaps_and_mementos(timemap_uris, output_directory, depth) 

    metadata_file.close()

#def build_collection_dict(collection_directory):
#
#    metadata = {}
#
#    timemap_dir = "{}/../../timemaps"
#    memento_dir = "{}/../../mementos"
#
#    metadata_filename = "{}/metadata.tsv".format(collection_directory)
#    metadata_file = open(metadata_filename)
#
#    
#
#    metadata_file.close()
