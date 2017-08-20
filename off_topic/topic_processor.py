import sys
import os
import nltk
from abc import ABCMeta, abstractmethod
from nltk.stem.porter import PorterStemmer
from boilerpipe.extract import Extractor
import distance
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import string
from decimal import Decimal
import json
import chardet

import pprint
pp = pprint.PrettyPrinter(indent=4)

stemmer = PorterStemmer()

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

    updated_filedata = {}

    for urit in filedata:

        mementos = filedata[urit]['mementos']

        for memento in mementos:

            logger.debug("removing boilerplate from: {}".format(memento))

            if memento['processed_for_off_topic'] == True:

                data_filename = memento['content_filename']

                logger.debug("processing file: {}".format(data_filename))
    
                output_filename = "{}.txt".format(data_filename)
    
                if not os.path.exists(output_filename):

                    ctype='utf-8'

                    if 'charset=' in memento['content-type']:
                        ctype = memento['content-type'].split('=')[1]

                    try:

                        with open(data_filename, encoding=ctype) as f:
                            input_data = f.read()

                    except UnicodeDecodeError as e:

                        try:
                            # TODO: opening the file twice is ridiculous
                            with open(data_filename, 'rb') as f:
                                data = f.read()

                                charset = chardet.detect(data)['encoding']

                            with open(data_filename, encoding=charset) as f:
                                input_data = f.read()

                        except UnicodeDecodeError as e:
                            logger.info("Can not determine character set "
                                "for URI-M: {}, skipping...".format(
                                memento['uri-m']))
   
                    if len(input_data) > 0:
                        extractor = Extractor(extractor='KeepEverythingExtractor', 
                            html=input_data)
    
                        boilerplate_text = extractor.getText()
                    else:
                        boilerplate_text = ''
    
                    with open(output_filename, 'w') as f:
                        f.write(boilerplate_text)
    
                memento['text-only_filename'] = output_filename

        updated_filedata[urit] = {}

        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata

def mark_unsupported_items(filedata):

    updated_filedata = {}

    for urit in filedata:

        mementos = filedata[urit]['mementos']

        for memento in mementos:

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
                        memento['uri-m'])

        updated_filedata.setdefault(urit, {})
        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata

def find_first_memento(memento_records):

    first_memento = None

    # sometimes there is an empty list...
    if len(memento_records) > 0:

        memento_list = []

        for memento in memento_records:

           if memento['processed_for_off_topic'] == True:

                memento_list.append( (
                    memento['memento-datetime'],
                    memento['uri-m']
                    ) )

        if len(memento_list) == 0:
            logger.info("NO MEMENTOS!!! Cannot find first memento!")
            logger.info(memento_records)
            return None

        first_memento = sorted(memento_list)[0]

        for memento in memento_records:
            if memento['uri-m'] == first_memento[1]:
                first_memento = memento
                break

    return first_memento


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

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])
    
                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
    
                first_mem_bcount = sys.getsizeof(''.join(first_tokens))
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['bytecount'] = first_mem_bcount
    
                for memento in updated_filedata[urit]['mementos']:
    
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
                    updated_filedata[urit]['mementos'][0].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][0]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][0]['measures']['off_topic_measure'] = 'only 1 memento'
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

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])
    
                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
                    first_tokens = remove_stop_words(first_tokens, self.stopwords)
    
                first_mem_wcount = len(first_tokens)
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['wordcount'] = first_mem_wcount
    
                for memento in updated_filedata[urit]['mementos']:

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
                    updated_filedata[urit]['mementos'][0].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][0]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][0]['measures']['off_topic_measure'] = 'only 1 memento'
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

                fileids = {}
                filesdata = {}

                mementos = updated_filedata[urit]['mementos']

                logger.debug("there are {} mementos for processing"
                    " under cosine similarity".format(len(mementos)))

                for i in range(0, len(mementos)):

                    if mementos[i]['processed_for_off_topic'] == True:

                        filename = mementos[i]['text-only_filename']
                        fileids[filename] = i 
    
                        with open(filename) as f:
                            filedata = f.read()
    
                        filesdata[filename] = filedata
                    else:
                        logger.debug("not processing memento at URI-M {}"
                            " for off topic".format(mementos[i]['uri-m']))

                logger.debug("discovered {} mementos for processing under"
                    " cosine similarity".format(len(filesdata)))

                logger.debug("mementos found: {}".format(updated_filedata[urit]['mementos']))

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                # sometimes there are no first memento because the mementos
                # are not able to be processed (i.e., not a supported format
                # like HTML)
                if first_mem != None:

                    first_mem_filename = first_mem['text-only_filename']
    
                    first = fileids[first_mem_filename]
 
                    tfidf_matrix = tfidf.fit_transform(filesdata.values())
    
                    csresults = cosine_similarity(tfidf_matrix[first], tfidf_matrix)
    
                    for i in range(0, len(csresults[0])):
                        mementos[i].setdefault('measures', {})
                        mementos[i]['measures']['cosine'] = Decimal(csresults[0][i])
                      
                        if 'on-topic' not in mementos[i]['measures']:
    
                            mementos[i]['measures']['on_topic'] = True
    
                            if Decimal(csresults[0][i]) < Decimal(self.threshold):
                                mementos[i]['measures']['on_topic'] = False
                                mementos[i]['measures']['off_topic_measure'] = \
                                    'cosine'

            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    updated_filedata[urit]['mementos'][0].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][0]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][0]['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata

class CosineSimilarityAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata):
        # eliminate every file that is not HTML, text
        updated_filedata = mark_unsupported_items(input_filedata)

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        # tokenizer removes stop words, hence stop_words = None
        tfidf = TfidfVectorizer(tokenizer=tokenize,
            stop_words=None)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                first_mem_filename = first_mem['text-only_filename']

                with open(first_mem['text-only_filename']) as f:
                    first_filedata = f.read()

                first_mem.setdefault('measures', {})

                for memento in updated_filedata[urit]['mementos']:

                    if memento['processed_for_off_topic'] == True:
                        filename = memento['text-only_filename']
                        logger.debug(
                            "working on file {} corresponding to URI-M {}"
                            .format( filename, memento['uri-m']))

                        with open(filename) as f:
                            filedata = f.read()

                        tfidf_matrix = tfidf.fit_transform(
                            [ first_filedata, filedata ]
                            )

                        csresults = cosine_similarity(
                            tfidf_matrix[0], tfidf_matrix[1])

                        memento.setdefault('measures', {})
                        memento['measures']['cosine'] = Decimal(csresults[0][0])

                        if 'on_topic' not in memento['measures']:
                            logger.debug("checking if URI-M {} is off-topic"
                                " with cosine score {} and threshold {}"
                                .format(memento['uri-m'], csresults[0][0],
                                self.threshold))
                        
                            memento['measures']['on_topic'] = True
                        
                            if Decimal(csresults[0][0]) < Decimal(self.threshold):
                                memento['measures']['on_topic'] = False
                                memento['measures']['off_topic_measure'] = \
                                    'cosine'
                                logger.debug("URI-M {} is off-topic".format(
                                    memento['uri-m']))

            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    updated_filedata[urit]['mementos'][0].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][0]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][0]['measures']['off_topic_measure'] = 'only 1 memento'
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

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            # also, if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
                    first_tokens = remove_stop_words(first_tokens, self.stopwords)

                for memento in updated_filedata[urit]['mementos']:

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
                    updated_filedata[urit]['mementos'][0].setdefault('measures', {}) 
                    updated_filedata[urit]['mementos'][0]['measures']['on_topic'] = True
                    updated_filedata[urit]['mementos'][0]['measures']['off_topic_measure'] = 'only 1 memento'
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

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                with open(first_mem['text-only_filename']) as f:
                    first_tf = self.generate_term_frequencies(f.read())

                for memento in updated_filedata[urit]['mementos']:
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
