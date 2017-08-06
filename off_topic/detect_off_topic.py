from bs4 import BeautifulSoup
import urllib2
import re
import sys
import os
sys.path.append("source_code")
import seed_extractor
import timemap_downloader
import argparse
import random
import html_wayback_downloader
import off_topic_detector_cos_sim
import off_topic_detector_count_words
import off_topic_detector_jaccard
import urlparse
import pprint

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

def create_scores_dict(filenames):

    scores_dict = {}

    for filename in filenames:

        with open(filename) as scorefile:

            for line in scorefile:
                line = line.strip()

                fields = line.split('\t')

                if fields[0] == "URIR_ID":
                    scorename = fields[3].replace('_score', '')
                else:
                    urir_id = fields[0]
                    mdatetime = fields[1]
                    memento_uri = fields[2]
                    score = fields[3]

                    scores_dict.setdefault(urir_id, {})
                    scores_dict[urir_id].setdefault(mdatetime, {})
                    scores_dict[urir_id][mdatetime]["uri-m"] = memento_uri
                    scores_dict[urir_id][mdatetime].setdefault("scores", {})
                    scores_dict[urir_id][mdatetime]["scores"][scorename] = float(score)

    return scores_dict
        
def determine_off_topic(score, threshold, comparison):

    off_topic = False

    if comparison == "<":

        if score < threshold:
            off_topic = True

    elif comparison == ">":

        if score > threshold:
            off_topic = True

    return off_topic

# thanks to https://www.tuxevara.de/2015/01/pythons-argparse-and-lists/
def arg_list(input_string):
    print "calling arg_list"
    print "returning {}".format(input_string.split(','))
    return input_string.split(',')

parser = argparse.ArgumentParser(prog="python {}".format(sys.argv[0]), description='Detecting off-topic webpages.')

parser.add_argument('-d', dest='dir', 
                   help='The directory that is used for the downloaded/processed data')
                   
#parser.add_argument('-th', dest='threshold', 
#                   help='The threshold to compute the off-topic pages between 0 to 1. The default threshold is 0.15')
                
parser.add_argument('-o', dest='file', 
                   help='The file path to write the output')

parser.add_argument('-t', dest='timemap_uri', 
                   help='The link of a timemap (it should be in timemap/link format)')

parser.add_argument('-i', dest='id', 
                   help='The collection id as appeared on archive-it')

parser.add_argument('-r', dest='uri', 
                   help='The collection uri as appeared on archive-it')

parser.add_argument('-m', dest='mode', default="cosim,wcount",
                   help='The similarity measure: cosim or wcount. The default is cosim.')

parser.add_argument('-c', dest='input_dir',
                    help='The already downloaded collection directory to use for data input.')

print "attempting to parse args..."

args = parser.parse_args()

print "args: {}".format(args)

data_directory = 'tmp'
if args.dir != None:
   data_directory =  args.dir
   
#threshold = 0.15
#if args.threshold != None:
#   threshold =  float(args.threshold)

output_file = sys.stdout
if args.file != None:
    output_file = open(args.file,'w')

if args.mode != None:
    mode = args.mode 
    
#    if mode != "cosim" and mode != "wcount" and mode != "jaccard":
#         parser.print_help()
#         sys.exit(1)
         
base_timemap_link_uri = "http://wayback.archive-it.org/"
download_mementos = True
if args.id !=None:
    # extract from id
    collection_id = args.id
    collection_directory = data_directory+"/collection_"+str(collection_id)
    seed_extractor.seed_extractor_from_id(collection_id,collection_directory)
    seed_list_file = collection_directory+"/seed_list.txt"
    collectionmap_file_name = collection_directory+"/collectionmap.txt"
    timemap_downloader.download(collectionmap_file_name, seed_list_file, base_timemap_link_uri+ str(collection_id)+"/timemap/link", collection_directory)
    
elif args.uri !=None:
    # extract from uri
    collection_uri = args.uri
    o = urlparse.urlparse(args.uri)
    collection_id = o.path.split('/')[-1]
    if collection_id == "":
        collection_id = o.path.split('/')[-2]
        
    collection_directory = data_directory+"/collection_"+str(collection_id)
    seed_list_file = collection_directory+"/seed_list.txt"
    collectionmap_file_name = collection_directory+"/collectionmap.txt"
    
    seed_extractor.seed_extractor_from_uri(collection_uri,collection_directory)
    timemap_downloader.download(collectionmap_file_name, seed_list_file, base_timemap_link_uri+str(collection_id)+"/timemap/link", collection_directory)
elif args.timemap_uri !=None:
    # extract directly from timemap
    memento_list = timemap_downloader.get_mementos_from_timemap(args.timemap_uri)
    collection_id = str(random.randrange(1000000))
    collection_directory = data_directory+"/collection_"+collection_id
    collectionmap_file_name =collection_directory+"/collectionmap.txt"
    ensure_dir(collectionmap_file_name)
    collectionmap_file =  open(collectionmap_file_name,'w')
    timemap_downloader.write_timemap_to_file(1, memento_list, collectionmap_file) 
    collectionmap_file.close()
elif args.input_dir !=None:
    #collection_directory = data_directory+"/collection_"+str(collection_id)
    collection_directory = args.input_dir
    seed_list_file = collection_directory+"/seed_list.txt"
    collectionmap_file_name = collection_directory+"/collectionmap.txt"
    download_mementos = False
else:
    parser.print_help() 

if download_mementos:
    html_wayback_downloader.download_html_from_wayback(collectionmap_file_name,collection_directory)      

os.system('./extract_text_from_html ' + collectionmap_file_name + ' ' + collection_directory)

off_topic_measures = {}

if ',' in mode:
    measures = mode.split(',')
else:
    measures = [ mode ]


for measure in measures:
    if measure == "cosim" :
        # TODO: change output_file to a cosine_scores_file
        off_topic_measures["cosine"] = {}
        off_topic_measures["cosine"]["score_file"] = collection_directory + "/cosine_scores.txt"
        off_topic_measures["cosine"]["default_threshold"] = 0.15
    
        # a cosine value of 1 means that 2 documents are equivalent
        off_topic_measures["cosine"]["threshold_comparison"] = "<" 
       
        with open(off_topic_measures["cosine"]["score_file"], 'w') as score_file:
            off_topic_detector_cos_sim.get_off_topic_memento(
                collectionmap_file_name, score_file, collection_directory)
    
    elif measure ==  "wcount":
        off_topic_measures["wcount"] = {}
        off_topic_measures["wcount"]["score_file"] = collection_directory + "/wordcount_scores.txt"
        off_topic_measures["wcount"]["default_threshold"] = -0.85
    
        # a word count difference of 0 means that 2 documents are equivalent,
        # but the threshold is less than 0
        off_topic_measures["wcount"]["threshold_comparison"] = "<" 
    
        with open(off_topic_measures["wcount"]["score_file"], 'w') as score_file:
            off_topic_detector_count_words.get_off_topic_memento(
                collectionmap_file_name, score_file, collection_directory)
    
    elif measure == 'jaccard':
        off_topic_measures["jaccard"] = {}
        off_topic_measures["jaccard"]["score_file"] = collection_directory + "/jaccard_scores.txt"
        off_topic_measures["jaccard"]["default_threshold"] = 0.05
    
        # a jaccard distance of 0 means that 2 documents are equivalent
        off_topic_measures["jaccard"]["threshold_comparison"] = ">" 
        
        with open(off_topic_measures["jaccard"]["score_file"], 'w') as score_file:
            off_topic_detector_jaccard.get_off_topic_memento(
                collectionmap_file_name, score_file, collection_directory)
    
    else:
        print "Skipping undefined measure {}"
        print "Supported measures: "
        print "cosine similarity (cosim), word count (wcount), Jaccard Distance (jaccard)"
        print

scores_filenames = []

for measure in off_topic_measures:
    scores_filenames.append(off_topic_measures[measure]["score_file"])

scores_dict = create_scores_dict(scores_filenames)

pp = pprint.PrettyPrinter(indent=4)
print
pp.pprint(off_topic_measures)
print
pp.pprint(scores_dict)

output_file.write("Measure\tSimilarity\tmemento_uri\n")

for measure in off_topic_measures:
    comparison = off_topic_measures[measure]["threshold_comparison"]
    threshold = off_topic_measures[measure]["default_threshold"]

    for urir_id in scores_dict:
        for mdatetime in scores_dict[urir_id]:
           
            try:
                score = scores_dict[urir_id][mdatetime]["scores"][measure]
                off_topic = determine_off_topic(score, threshold, comparison)

                if off_topic:
                    memento_uri = scores_dict[urir_id][mdatetime]["uri-m"]
                    output_file.write("{}\t{}\t{}\n".format(measure, score, memento_uri))
            except KeyError as e:
                for measure in off_topic_measures:
                    if measure in e.message:
                        print "No {} measure for URIR_ID {} at datetime {}".format(measure, urir_id, mdatetime)
                        break
