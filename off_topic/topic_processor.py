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

import pprint
pp = pprint.PrettyPrinter(indent=4)

stemmer = PorterStemmer()

def load_stopwords():
    f = open('stopwords.txt')
    stopwords =[]
    for w in f:
        stopwords.append(w.replace('\r','').replace('\n',''))
    return stopwords

def stem_tokens(tokens):
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed

def remove_stop_words(tokens):
    
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

            data_filename = memento['content_filename']

            output_filename = "{}.txt".format(data_filename)

            if not os.path.exists(output_filename):

                with open(data_filename) as f:
                    input_data = f.read()

                extractor = Extractor(extractor='KeepEverythingExtractor', 
                    html=input_data)

                boilerplate_text = extractor.getText()

                with open(output_filename, 'w') as f:
                    f.write(boilerplate_text)

            memento['text-only_filename'] = output_filename

        updated_filedata[urit] = {}

        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata

def find_first_memento(memento_records):

    # sometimes there is an empty list...
    if len(memento_records) > 0:

        memento_list = []

        for memento in memento_records:
            memento_list.append( (
                memento['memento-datetime'],
                memento['uri-m']
                ) )

        if len(memento_list) == 0:
            print("NO MEMENTOS!!!")
            print(memento_records)
            return

        first_memento = sorted(memento_list)[0]

        for memento in memento_records:
            if memento['uri-m'] == first_memento[1]:
                first_memento = memento
                break

    return first_memento


class TopicProcessor(metaclass=ABCMeta):

    def __init__(self, threshold, working_directory, logger):
        self.threshold = threshold
        self.working_directory = working_directory
        self.logger = logger

        self.stopwords = load_stopwords()

    @abstractmethod
    def get_scores(self, input_filedata):
        pass

class ByteCountAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # TODO: eliminate every file that is not HTML, text

        # strip all tags out of all remaining content
        updated_filedata = self.remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])
    
                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
    
                first_mem_bcount = sys.getsizeof(''.join(first_tokens))
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['bytecount'] = first_mem_bcount
    
                for memento in updated_filedata[urit]['mementos']:
    
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
                self.logger.info(
                    "TimeMap for {} has no mementos, skipping...".format(
                    urit))

        return updated_filedata

class WordCountAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # TODO: eliminate every file that is not HTML, text

        # strip all tags out of all remaining content
        updated_filedata = self.remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = self.find_first_memento(
                    updated_filedata[urit]['mementos'])
    
                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
                    first_tokens = remove_stop_words(first_tokens)
    
                first_mem_wcount = len(first_tokens)
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['wordcount'] = first_mem_wcount
    
                for memento in updated_filedata[urit]['mementos']:
    
                    with open(memento['text-only_filename']) as f:
                        # tokenize, stemming, remove stop words
                        tokens = tokenize(f.read())
                        tokens = remove_stop_words(tokens)
    
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
                self.logger.info(
                    "TimeMap for {} has no mementos, skipping...".format(
                    urit))

        return updated_filedata


class CosineSimilarityAgainstTimeMap(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        # tokenizer removes stop words, hence stop_words = None
        tfidf = TfidfVectorizer(tokenizer=tokenize,
            stop_words=self.stopwords)

        for urit in updated_filedata:

            self.logger.info("processing data for Timemap {} using cosine similarity"
                .format(urit))

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                fileids = {}
                filesdata = {}

                mementos = updated_filedata[urit]['mementos']

                for i in range(0, len(mementos)):
                    filename = mementos[i]['text-only_filename']
                    fileids[filename] = i 

                    with open(filename) as f:
                        filedata = f.read()

                    filesdata[filename] = filedata

                self.logger.info("discovered {} mementos for processing under"
                    " cosine similarity".format(len(filesdata)))

                self.logger.info("mementos found: {}".format(updated_filedata[urit]['mementos']))

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

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

        return updated_filedata

class CosineSimilarityAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # TODO: eliminate everything that is not HTML, text, or PDF

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        # tokenizer removes stop words, hence stop_words = None
        tfidf = TfidfVectorizer(tokenizer=tokenize,
            stop_words=None)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                first_mem_filename = first_mem['text-only_filename']

                with open(first_mem['text-only_filename']) as f:
                    first_filedata = f.read()

                first_mem.setdefault('measures', {})

                for memento in updated_filedata[urit]['mementos']:

                    filename = memento['text-only_filename']
                    self.logger.debug(
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
                        self.logger.info("checking if URI-M {} is off-topic"
                            " with cosine score {} and threshold {}"
                            .format(memento['uri-m'], csresults[0][0],
                            self.threshold))
                    
                        memento['measures']['on_topic'] = True
                    
                        if Decimal(csresults[0][0]) < Decimal(self.threshold):
                            memento['measures']['on_topic'] = False
                            memento['measures']['off_topic_measure'] = \
                                'cosine'
                            self.logger.info("URI-M {} is off-topic".format(
                                memento['uri-m']))

        return updated_filedata 

class JaccardDistanceAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # TODO: eliminate everything that is not HTML, text, or PDF

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                with open(first_mem['text-only_filename']) as f:
                    first_tokens = tokenize(f.read())
                    first_tokens = remove_stop_words(first_tokens)

                for memento in updated_filedata[urit]['mementos']:

                    with open(memento['text-only_filename']) as f:
                        # tokenize, stemming, remove stop words
                        tokens = tokenize(f.read())
                        tokens = remove_stop_words(tokens)

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
                self.logger.info(
                    "TimeMap for {} has no mementos, skipping...".format(
                    urit))

        return updated_filedata

class TFIntersectionAgainstSingleResource(TopicProcessor):

    def score_term_frequencies(self, term_frequencies1, term_frequencies2):

        return len([i for i, j in zip(term_frequencies1, term_frequencies2)
            if i != j])

    def generate_term_frequencies(self, data):

        tokens = tokenize(data) 
        tokens = remove_stop_words(tokens)

        term_frequencies = []

        for token in set(tokens):
            token_count = tokens.count(token)

            term_frequencies.append( (token_count, token) )

        return sorted(term_frequencies, reverse=True)

    def get_scores(self, input_filedata, score_data):

        # strip all tags out of all remaining content
        updated_filedata = remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = find_first_memento(
                    updated_filedata[urit]['mementos'])

                with open(first_mem['text-only_filename']) as f:
                    first_tf = self.generate_term_frequencies(f.read())

                for memento in updated_filedata[urit]['mementos']:

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
                self.logger.info(
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

def get_topic_processor(measure, threshold, working_directory, logger):
    return supported_measures[measure]['class'](
        threshold, working_directory, logger)
