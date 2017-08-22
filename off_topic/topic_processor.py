import sys
import os
import nltk
from abc import ABCMeta, abstractmethod
from nltk.stem.porter import PorterStemmer
# This did not work in all cases, went the Java route instead
#from boilerpipe.extract import Extractor
import distance
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import string
from decimal import Decimal
import json
import chardet
import logging

import pprint
pp = pprint.PrettyPrinter(indent=4)

stemmer = PorterStemmer()

def generate_logger():

    logger = logging.getLogger(__name__)
    logger.propagate = False

    ch = logging.StreamHandler()
#    ch.setLevel(logging.WARNING)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = generate_logger()
logger.setLevel(logging.INFO)
logger.info("info from {}".format(__name__))

def load_stopwords():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    with open('{}/stopwords.txt'.format(dir_path)) as f:
        stopwords =[]
        for w in f:
            stopwords.append(w.replace('\r','').replace('\n',''))

    return stopwords

def stem_tokens(tokens):
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed

def remove_stop_words(tokens, stopwords):
    
    # remove stop words
    tokens = [ i for i in tokens if i not in stopwords ]

    return tokens

def tokenize(text):
    tokens = nltk.word_tokenize(text)
    stems = stem_tokens(tokens)

    # remove punctuation
    tokens = [ i for i in tokens if i not in string.punctuation ]

    return tokens

def remove_boilerplate(filedata):

    # TODO: this function performs quite poorly because of the number of 
    # calls out to the shell to call Java's boilerpipe, the Python
    # boilerpipe could not handle some files with ambiguous character sets

    updated_filedata = {}
    this_file_dir = os.path.dirname(os.path.realpath(__file__))
    original_dir = os.getcwd()

    for urit in filedata:

        mementos = filedata[urit]['mementos']

        for urim in mementos:

            memento = mementos[urim]

            logger.debug("removing boilerplate from: {}".format(memento))

            if memento['processed_for_off_topic'] == True:

                data_filename = memento['content_filename']

                logger.debug("processing file: {}".format(data_filename))
    
                output_filename = "{}.txt".format(data_filename)
    
                if not os.path.exists(output_filename):

                    os.chdir("{}/java_off_topic".format(this_file_dir))

                    os.system("./ExtractTextFromHTML {} {}".format(data_filename, output_filename))

                    os.chdir(original_dir)
    
                memento['text-only_filename'] = output_filename

        updated_filedata[urit] = {}

        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata

def mark_unsupported_items(filedata):

    updated_filedata = {}

    for urit in filedata:

        mementos = filedata[urit]['mementos']

        for urim in mementos:

            memento = mementos[urim]

            with open(memento['headers_filename']) as f:
                json_headers = json.load(f)

                headers = {}

                for key in json_headers:
                    headers[key.lower()] = json_headers[key]

            if 'content-type' in headers:
                if 'text/html' in headers['content-type']:
                    memento['processed_for_off_topic'] = True
                    memento['content-type'] = headers['content-type']

                else:
                    memento['processed_for_off_topic'] = \
                        'unsupported file format {} for memento at {}'.format(
                            headers['content-type'], memento['uri-m'])
                    memento['content-type'] = headers['content-type']

            else:
                memento['processed_for_off_topic'] =  \
                    'no content-type header for memento at {}'.format(
                        urim)

        updated_filedata.setdefault(urit, {})
        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata

def find_first_memento(memento_records):

    first_urim = None

    # sometimes there is an empty list...
    if len(memento_records) > 0:

        memento_list = []

        for urim in memento_records:

            memento = memento_records[urim]

            if memento['processed_for_off_topic'] == True:

                memento_list.append( (
                    memento['memento-datetime'],
                    urim
                    ) )

        if len(memento_list) == 0:
            logger.warn("Cannot find first memento in TimeMap!"
                " This is likely because all mementos in this TimeMap"
                " use an unsupported or unknown content-type.")
            logger.debug("no mementos in records: {}".format(memento_records))
            return None

        first_memento = sorted(memento_list)[0]

        for urim in memento_records:
            if urim == first_memento[1]:
                first_urim = urim 
                break

    return first_urim


class TopicProcessor(metaclass=ABCMeta):

    def __init__(self, threshold):
        self.threshold = threshold

        self.stopwords = load_stopwords()

    @abstractmethod
    def get_scores(self, input_filedata):
        pass

class ByteCountAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata):

        # trash in, trash out
        if input_filedata == None:
            return None

        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 0:

                mementos = updated_filedata[urit]['mementos']

                first_urim = find_first_memento(
                    updated_filedata[urit]['mementos'])
  
                if first_urim != None:

                    with open(mementos[first_urim]['text-only_filename']) as f:
                        first_tokens = tokenize(f.read())
        
                    first_mem_bcount = sys.getsizeof(''.join(first_tokens))
        
                    mementos[first_urim].setdefault('measures', {})
                    mementos[first_urim]['measures']['bytecount'] = first_mem_bcount
        
                    for urim in mementos:
    
                        memento = mementos[urim]
        
                        if memento['processed_for_off_topic'] == True:
    
                            with open(memento['text-only_filename']) as f:
                                # tokenize, stemming, remove stop words
                                tokens = tokenize(f.read())
        
                            # calculate the word count on all documents
                            bcount = len(tokens)
                            
                            memento.setdefault('measures', {})
                            
                            # compare the word count of all documents with 
                            # the first in TimeMap
                            bcount_diff = bcount - first_mem_bcount
                            bcount_diff_pc = bcount_diff / float(first_mem_bcount)
    
                            # the difference percentage is what is important
                            memento['measures']['bytecount'] = bcount_diff_pc
                            
                            if 'on_topic' not in memento['measures']:
                            
                                memento['measures']['on_topic'] = True
                            
                                if bcount_diff_pc < self.threshold:
                                    memento['measures']['on_topic'] = False
                                    memento['measures']['off_topic_measure'] = \
                                        'bytecount'
            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    urim = list(updated_filedata[urit]['mementos'].keys())[0]
                    updated_filedata[urit]['mementos'][urim].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][urim]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][urim]['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata

class WordCountAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata):

        # trash in, trash out
        if input_filedata == None:
            return None

        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                mementos = updated_filedata[urit]['mementos']

                first_urim = find_first_memento(
                    updated_filedata[urit]['mementos'])
  
                if first_urim != None:

                    with open(mementos[first_urim]['text-only_filename']) as f:
                        first_tokens = tokenize(f.read())
                        first_tokens = remove_stop_words(first_tokens, self.stopwords)
        
                    first_mem_wcount = len(first_tokens)
        
                    mementos[first_urim].setdefault('measures', {})
                    mementos[first_urim]['measures']['wordcount'] = first_mem_wcount
    
                    for urim in mementos:
    
                        memento = mementos[urim]
    
                        if memento['processed_for_off_topic'] == True:
    
                            with open(memento['text-only_filename']) as f:
                                # tokenize, stemming, remove stop words
                                tokens = tokenize(f.read())
                                tokens = remove_stop_words(tokens, self.stopwords)
        
                            # calculate the word count on all documents
                            wcount = len(tokens)
                            
                            memento.setdefault('measures', {})
                            
                            # compare the word count of all documents with 
                            # the first in TimeMap
                            wcount_diff = wcount - first_mem_wcount
                            wcount_diff_pc = wcount_diff / float(first_mem_wcount)
    
                            # the difference percentage is what is important
                            memento['measures']['wordcount'] = wcount_diff_pc
                            
                            if 'on_topic' not in memento['measures']:
                            
                                memento['measures']['on_topic'] = True
                            
                                if wcount_diff_pc < self.threshold:
                                    memento['measures']['on_topic'] = False
                                    memento['measures']['off_topic_measure'] = \
                                        'wordcount'
            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    urim = list(updated_filedata[urit]['mementos'].keys())[0]
                    updated_filedata[urit]['mementos'][urim].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][urim]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][urim]['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata


class CosineSimilarityAgainstTimeMap(TopicProcessor):

    def get_scores(self, input_filedata):

        # trash in, trash out
        if input_filedata == None:
            return None

        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        # tokenizer removes stop words, hence stop_words = None
        tfidf = TfidfVectorizer(tokenizer=tokenize,
            stop_words=self.stopwords)

        for urit in updated_filedata:

            logger.debug("processing data for Timemap {} using cosine similarity"
                .format(urit))

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                filesdata = []
                urims = []

                mementos = updated_filedata[urit]['mementos']

                logger.debug("there are {} mementos for processing"
                    " under cosine similarity".format(len(mementos)))

                for urim in mementos:

                    memento = mementos[urim]

                    if memento['processed_for_off_topic'] == True:

                        filename = memento['text-only_filename']
    
                        with open(filename) as f:
                            filedata = f.read()
   
                        # the index for filesdata must correspond to the index
                        # in urims for this to work
                        filesdata.append(filedata)
                        urims.append(urim)
                    else:
                        logger.debug("not processing memento at URI-M {}"
                            " for off topic".format(urim))

                logger.debug("discovered {} mementos for processing under"
                    " cosine similarity".format(len(filesdata)))

                logger.debug("mementos found: {}".format(updated_filedata[urit]['mementos']))

                first_urim = find_first_memento(
                    updated_filedata[urit]['mementos'])

                # sometimes there are no first memento because the mementos
                # are not able to be processed (i.e., not a supported format
                # like HTML)
                if first_urim != None:

                    first = urims.index(first_urim)
 
                    tfidf_matrix = tfidf.fit_transform(filesdata)
    
                    csresults = cosine_similarity(tfidf_matrix[first], tfidf_matrix)
   
                    # TODO: this solution assumes that the positions between .values()
                    # and .keys() for a dict are the same
                    for i in range(0, len(csresults[0])):

                        urim = urims[i]

                        logger.debug("processing memento {}".format(mementos[urim]))
                        mementos[urim].setdefault('measures', {})
                        mementos[urim]['measures']['cosine'] = Decimal(csresults[0][i])
                        logger.debug("memento should now have scores {}".format(mementos[urim]))
                      
                        if 'on-topic' not in mementos[urim]['measures']:
    
                            mementos[urim]['measures']['on_topic'] = True
    
                            if Decimal(csresults[0][i]) < Decimal(self.threshold):
                                mementos[urim]['measures']['on_topic'] = False
                                mementos[urim]['measures']['off_topic_measure'] = \
                                    'cosine'

                        logger.debug("memento should now have on-topic score {}".format(mementos[urim]))

            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    urim = list(updated_filedata[urit]['mementos'].keys())[0]
                    updated_filedata[urit]['mementos'][urim].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][urim]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][urim]['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata

class JaccardDistanceAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata):

        # trash in, trash out
        if input_filedata == None:
            return None

        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            mementos = updated_filedata[urit]['mementos']

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                first_urim = find_first_memento(
                    updated_filedata[urit]['mementos'])

                if first_urim != None:

                    with open(mementos[first_urim]['text-only_filename']) as f:
                        first_tokens = tokenize(f.read())
                        first_tokens = remove_stop_words(first_tokens, self.stopwords)
    
                    for urim in mementos:
    
                        memento = mementos[urim]
    
                        if memento['processed_for_off_topic'] == True:
                            with open(memento['text-only_filename']) as f:
                                # tokenize, stemming, remove stop words
                                tokens = tokenize(f.read())
                                tokens = remove_stop_words(tokens, self.stopwords)
    
                            jdist = distance.jaccard(tokens, first_tokens)
    
                            memento.setdefault('measures', {})
                            memento['measures']['jaccard'] = jdist
    
                            if 'on_topic' not in memento['measures']:
                            
                                memento['measures']['on_topic'] = True
                            
                                if jdist > self.threshold:
                                    memento['measures']['on_topic'] = False
                                    memento['measures']['off_topic_measure'] = \
                                        'jaccard'
            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    urim = list(updated_filedata[urit]['mementos'].keys())[0]
                    updated_filedata[urit]['mementos'][urim].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][urim]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][urim]['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata

class TFIntersectionAgainstSingleResource(TopicProcessor):

    def score_term_frequencies(self, term_frequencies1, term_frequencies2):

        return len([i for i, j in zip(term_frequencies1, term_frequencies2)
            if i != j])

    def generate_term_frequencies(self, data):

        tokens = tokenize(data) 
        tokens = remove_stop_words(tokens, self.stopwords)

        term_frequencies = []

        for token in set(tokens):
            token_count = tokens.count(token)

            term_frequencies.append( (token_count, token) )

        return sorted(term_frequencies, reverse=True)

    def get_scores(self, input_filedata):

        # trash in, trash out
        if input_filedata == None:
            return None

        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:
                
                mementos = updated_filedata[urit]['mementos']

                first_urim = find_first_memento(
                    updated_filedata[urit]['mementos'])

                if first_urim != None:

                    with open(mementos[first_urim]['text-only_filename']) as f:
                        first_tf = self.generate_term_frequencies(f.read())
    
                    for urim in mementos:
    
                        memento = mementos[urim]
    
                        if memento['processed_for_off_topic'] == True:
    
                            with open(memento['text-only_filename']) as f:
                                # tokenize, stemming, remove stop words
                                current_tf = self.generate_term_frequencies(f.read())
    
                            tfdist = self.score_term_frequencies(
                                first_tf[0:20], current_tf[0:20])
    
                            memento.setdefault('measures', {})
                            memento['measures']['tfintersection'] = tfdist
    
                            if 'on_topic' not in memento['measures']:
                            
                                memento['measures']['on_topic'] = True
                            
                                if tfdist > self.threshold:
                                    memento['measures']['on_topic'] = False
                                    memento['measures']['off_topic_measure'] = \
                                        'tfintersection'
            else:
                logger.info(
                    "TimeMap for {} has no mementos, skipping...".format(
                    urit))

        return updated_filedata


supported_measures = {
    'cosine': {
        'name': 'Cosine Similarity',
        'default_threshold': 0.15,
        'class': CosineSimilarityAgainstTimeMap
    },
    'jaccard': {
        'name': 'Jaccard Distance',
        'default_threshold': 0.05,
        'class': JaccardDistanceAgainstSingleResource
    },
    'wordcount': {
        'name': 'Word Count',
        'default_threshold': -0.85,
        'class': WordCountAgainstSingleResource
    },
    'bytecount': {
        'name': 'Byte Count',
        'default_threshold': -0.65,
        'class': ByteCountAgainstSingleResource
    },
    'tfintersection': {
        'name': 'TF-Intersection',
        'default_threshold': 0,
        'class': TFIntersectionAgainstSingleResource
    }
}

def get_topic_processor(measure, threshold):
    return supported_measures[measure]['class'](threshold)
