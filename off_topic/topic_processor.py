import os
import nltk
from abc import ABCMeta, abstractmethod
from nltk.stem.porter import PorterStemmer
from boilerpipe.extract import Extractor
import distance
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import string

import pprint
pp = pprint.PrettyPrinter(indent=4)

class TopicProcessor(metaclass=ABCMeta):

    def __init__(self, threshold, working_directory, logger):
        self.threshold = threshold
        self.working_directory = working_directory
        self.logger = logger

        self.stemmer = PorterStemmer()
        self.stopwords = self.load_stopwords()

    def load_stopwords(self):
        f = open('stopwords.txt')
        stopwords =[]
        for w in f:
            stopwords.append(w.replace('\r','').replace('\n',''))
        return stopwords
    
    def stem_tokens(self, tokens, stemmer):
        stemmed = []
        for item in tokens:
            stemmed.append(self.stemmer.stem(item))
        return stemmed
    
    def tokenize(self, text):
        tokens = nltk.word_tokenize(text)
        stems = self.stem_tokens(tokens, self.stemmer)

        # remove stop words
        tokens = [ i for i in stems if i not in self.stopwords ]

        tokens = [ i for i in tokens if i not in string.punctuation ]

        return tokens

    def remove_boilerplate(self, filedata):

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

                    #print("boilerplate_text: {}".format(boilerplate_text))
                    #return

                    with open(output_filename, 'w') as f:
                        f.write(boilerplate_text)

                memento['text-only_filename'] = output_filename

            updated_filedata[urit] = {}

            updated_filedata[urit]['mementos'] = mementos

        return updated_filedata

    def find_first_memento(self, memento_records):

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

                first_mem = self.find_first_memento(
                    updated_filedata[urit]['mementos'])
    
                with open(first_mem['text-only_filename']) as f:
                    first_tokens = self.tokenize(f.read())
    
                first_mem_bcount = ''.join(first_tokens)
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['bcount'] = first_mem_bcount
    
                for memento in updated_filedata[urit]['mementos']:
    
                    with open(memento['text-only_filename']) as f:
                        # tokenize, stemming, remove stop words
                        tokens = self.tokenize(f.read())
    
                    # calculate the word count on all documents
                    wcount = len(tokens)
                    
                    memento.setdefault('measures', {})
                    memento['measures']['bcount'] = wcount
                    
                    # compare the word count of all documents with 
                    # the first in TimeMap
                    bcount_diff = first_mem_wcount - \
                        memento['measures']['bcount']
                    
                    if 'on_topic' not in memento['measures']:
                    
                        memento['measures']['on_topic'] = True
                    
                        if wcount_diff < self.threshold:
                            memento['measures']['on_topic'] = False
                            memento['measures']['off_topic_measure'] = \
                                'bcount'
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
                    first_tokens = self.tokenize(f.read())
    
                first_mem_wcount = len(first_tokens)
    
                first_mem.setdefault('measures', {})
                first_mem['measures']['wcount'] = first_mem_wcount
    
                for memento in updated_filedata[urit]['mementos']:
    
                    with open(memento['text-only_filename']) as f:
                        # tokenize, stemming, remove stop words
                        tokens = self.tokenize(f.read())
    
                    # calculate the word count on all documents
                    wcount = len(tokens)
                    
                    memento.setdefault('measures', {})
                    memento['measures']['wcount'] = wcount
                    
                    # compare the word count of all documents with 
                    # the first in TimeMap
                    wcount_diff = first_mem_wcount - \
                        memento['measures']['wcount']
                    
                    if 'on_topic' not in memento['measures']:
                    
                        memento['measures']['on_topic'] = True
                    
                        if wcount_diff < self.threshold:
                            memento['measures']['on_topic'] = False
                            memento['measures']['off_topic_measure'] = \
                                'wcount'
            else:
                self.logger.info(
                    "TimeMap for {} has no mementos, skipping...".format(
                    urit))

        return updated_filedata


class CosineSimilarityAgainstSingleResource(TopicProcessor):

    def get_scores(self, input_filedata, score_data):
        # TODO: eliminate everything that is not HTML, text, or PDF

        # strip all tags out of all remaining content
        updated_filedata = self.remove_boilerplate(input_filedata)

        # tokenizer removes stop words, hence stop_words = None
        tfidf = TfidfVectorizer(tokenizer=self.tokenize,
            stop_words=None)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = self.find_first_memento(
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
                    memento['measures']['cosine'] = csresults[0]

                    if 'on_topic' not in memento['measures']:
                        self.logger.info("checking if URI-M {} is off-topic"
                            " with cosine score {}"
                            .format(memento['uri-m'], csresults[0]))
                    
                        memento['measures']['on_topic'] = True
                    
                        if csresults[0] < self.threshold:
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
        updated_filedata = self.remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = self.find_first_memento(
                    updated_filedata[urit]['mementos'])

                with open(first_mem['text-only_filename']) as f:
                    first_tokens = self.tokenize(f.read())

                for memento in updated_filedata[urit]['mementos']:

                    with open(memento['text-only_filename']) as f:
                        # tokenize, stemming, remove stop words
                        tokens = self.tokenize(f.read())

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

        tokens = self.tokenize(data) 

        term_frequencies = []

        for token in set(tokens):
            token_count = tokens.count(token)

            term_frequencies.append( (token_count, token) )

        return sorted(term_frequencies, reverse=True)

    def get_scores(self, input_filedata, score_data):

        # strip all tags out of all remaining content
        updated_filedata = self.remove_boilerplate(input_filedata)

        for urit in updated_filedata:

            # some TimeMaps have no mementos
            # e.g., http://wayback.archive-it.org/3936/timemap/link/http://www.peacecorps.gov/shutdown/?from=hpb
            if len(updated_filedata[urit]['mementos']) > 0:

                first_mem = self.find_first_memento(
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
                    
                        if jdist > self.threshold:
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
        'class': CosineSimilarityAgainstSingleResource
    },
    'jaccard': {
        'name': 'Jaccard Distance',
        'default_threshold': 0.05,
        'class': JaccardDistanceAgainstSingleResource
    },
    'wcount': {
        'name': 'Word Count',
        'default_threshold': -0.85,
        'class': WordCountAgainstSingleResource
    },
    'bytecount': {
        'name': 'Byte Count',
        'default_threshold': -0.65,
        'class': WordCountAgainstSingleResource
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
