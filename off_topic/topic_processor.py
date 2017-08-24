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
import tempfile

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

def load_stopwords():
    """
        AlNoamany's original function for loading stopwords from the English
        stopword file generated as part of her research.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))

    with open('{}/stopwords.txt'.format(dir_path)) as f:
        stopwords =[]
        for w in f:
            stopwords.append(w.replace('\r','').replace('\n',''))

    return stopwords

def stem_tokens(tokens, stemmer):
    """
        AlNoamany's original function for stemming tokens.
    """
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed

def remove_stop_words(tokens, stopwords):
    """
        This function removes the stopwords from the given list of tokens.
    """
    # remove stop words
    tokens = [ i for i in tokens if i not in stopwords ]

    return tokens

def tokenize(text):
    """
        AlNoamany's original function for tokenizing text.
    """
    tokens = nltk.word_tokenize(text)
    stems = stem_tokens(tokens, stemmer)
    return stems

def tokenize_without_punctuation(text):
    """
        An updated tokenizing function that tokenizes text and removes 
        punctuation.
    """
    tokenize(text)

    # remove punctuation
    tokens = [ i for i in tokens if i not in string.punctuation ]

    return tokens

def remove_boilerplate(filedata):
    """
        For each memento in filedata, this function removes its boilerplate
        (i.e, HTML tags). The resulting boilerplate-free files are stored
        in the same directory as the downloaded memento content with an 
        appended file extension of ".txt".

        This function detects the existence of files from previous runs.
    """

    # TODO: this function actually executes a Java program because
    # Python boilerpipe could not handle some files with ambiguous
    # character sets

    updated_filedata = {}
    this_file_dir = os.path.dirname(os.path.realpath(__file__))
    original_dir = os.getcwd()

    tfn = tempfile.mkstemp("topic_processor")[1]

    with open(tfn, 'w') as tf:

        for urit in filedata:
    
            mementos = filedata[urit]['mementos']
    
            for urim in mementos:
    
                memento = mementos[urim]
    
                if memento['processed_for_off_topic'] == True:
    
                    data_filename = memento['content_filename']
                    to_filename = "{}.txt".format(data_filename)
    
                    if not os.path.exists(to_filename):
                        tf.write("{}\n".format(data_filename))
    
                    # TODO: I feel like this should only be inserted if the
                    # text-only filename actually exists
                    memento['text-only_filename'] = to_filename
        
            updated_filedata[urit] = {}
        
            updated_filedata[urit]['mementos'] = mementos

    logger.info("removing boilerplate from files")

    os.chdir("{}/java_off_topic".format(this_file_dir))
    os.system("./ExtractTextFromHTMLFiles {}".format(tf.name))
    os.chdir(original_dir)

    logger.info("removing temporary file {}".format(tf.name))

    return updated_filedata

def mark_unsupported_items(filedata):
    """
        Rather than deleting the mementos from the data structure
        we mark them with a reason for why they are not processed.

        This way, one can find out why without digging through this
        library's code.

        This function detects those mementos that have an unsupported
        content-type so that we do not process them.
    """

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

def find_first_supported_urim(memento_records):
    """
        Find the first URI-M that is of a supported content type
        by memento-datetime in a set of memento records.
    """

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
            logger.warning("Cannot find first memento in TimeMap!"
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

def mark_empty_mementos(filedata):
    """
        Rather than deleting the mementos from the data structure
        we mark them with a reason for why they are not processed.

        This way, one can find out why without digging through this
        library's code.

        This function just detects those mementos that have no content.
    """

    updated_filedata = {}

    for urit in filedata:

        mementos = filedata[urit]['mementos']

        for urim in mementos:

            memento = mementos[urim]

            fsize = os.stat(memento['content_filename']).st_size

            if fsize == 0:
                memento['processed_for_off_topic'] =  \
                    'content size is zero for memento at {}'.format(
                        urim)

        updated_filedata.setdefault(urit, {})
        updated_filedata[urit]['mementos'] = mementos

    return updated_filedata
   
def get_clean_memento_data(input_filedata):
    """
        This function provides one place to consistently clean
        the memento data before it is processed by one or more
        similarity measures.
    """

    # trash in, trash out
    if input_filedata == None:
        return None

    updated_filedata = input_filedata

    # eliminate every file that is not HTML, text
    updated_filedata = mark_unsupported_items(updated_filedata)

    # eliminate empty mementos
    updated_filedata = mark_empty_mementos(updated_filedata)
    
    # strip all tags out of all remaining content
    updated_filedata = remove_boilerplate(updated_filedata)

    return updated_filedata


class TopicProcessor(metaclass=ABCMeta):

    def __init__(self, threshold):
        self.threshold = threshold

        self.stopwords = load_stopwords()

    @abstractmethod
    def get_scores(self, input_filedata):
        pass

    @abstractmethod
    def memento_scorefunction(self, mementos, *args):
        pass

    def compute_scores_for_mementos_in_TimeMap(
        self, scorefunction, input_filedata, *args):
        """
            Compute the scores for the mementos in each given TimeMap
            found in input_filedata using the function supplied in 
            scorefunction.

            The args function is for supplying additional optional
            arguments that may be passed to the necessary scorefunction,
            such as a TFIDF vector object.

            Note that this is not performed against the whole collection,
            but is used by AlNoamany's initial algorithms.
        """

        # only work with cleaned data
        updated_filedata = get_clean_memento_data(input_filedata)

        if updated_filedata == None:
            return None

        for urit in updated_filedata:

            # if there is only 1 memento, it isn't really off-topic, is it?
            if len(updated_filedata[urit]['mementos']) > 1:

                mementos = updated_filedata[urit]['mementos']

                first_urim = find_first_supported_urim(mementos)

                # the first memento may not be found because no mementos are
                # of a supported content type
                if first_urim != None:
                    updated_mementos = scorefunction(mementos, first_urim,
                        args)

                    updated_filedata[urit]['mementos'] = updated_mementos
                else:
                    logger.info("TimeMap for {} has no mementos with "
                        "supported content types, skipping...".format(urit))
                    for urim in mementos:
                        memento = mementos[urim]
                        memento.setdefault('measures', {}) 
                        # This should probably be set to something other than 
                        # True if we couldn't measure the memento
                        memento['measures']['on_topic'] = True
                        memento['measures']['off_topic_measure'] = \
                            'unsupported content-type for memento'

            else:
                if len(updated_filedata[urit]['mementos']) == 1:
                    urim = list(updated_filedata[urit]['mementos'].keys())[0]
                    memento = updated_filedata[urit]['mementos'][urim]
                    memento.setdefault('measures', {}) 
                    memento['measures']['on_topic'] = True
                    memento['measures']['off_topic_measure'] = 'only 1 memento'
                else:
                    # some TimeMaps have no mementos
                    # e.g., http://wayback.archive-it.org/3936/timemap/link
                    # /http://www.peacecorps.gov/shutdown/?from=hpb
                    logger.info(
                        "TimeMap for {} has no mementos, skipping...".format(
                        urit))

        return updated_filedata

class ByteCountAgainstSingleResource(TopicProcessor):

    def memento_scorefunction(self, mementos, first_urim, *args):

        logger.debug("there are {} mementos for processing"
            " under byte count".format(len(mementos)))

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
        
                # calculate the byte count on all documents
                bcount = sys.getsizeof(''.join(tokens))
                
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

        return mementos

    def get_scores(self, input_filedata):

        updated_filedata = self.compute_scores_for_mementos_in_TimeMap(
            self.memento_scorefunction, input_filedata)

        return updated_filedata

class WordCountAgainstSingleResource(TopicProcessor):

    def memento_scorefunction(self, mementos, first_urim, *args):

        logger.debug("there are {} mementos for processing"
            " under word count".format(len(mementos)))

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

        return mementos

    def get_scores(self, input_filedata):

        updated_filedata = self.compute_scores_for_mementos_in_TimeMap(
            self.memento_scorefunction, input_filedata)

        return updated_filedata


class CosineSimilarityAgainstTimeMap(TopicProcessor):

    def memento_scorefunction(self, mementos, first_urim, *args):

        # function signature matches the abstract function, so we have to
        # extract the tfidf object
        tfidf = args[0][0]

        filesdata = []
        urims = []
        filenames = []

        logger.debug("there are {} mementos for processing"
            " under cosine similarity".format(len(mementos)))

        translator = str.maketrans('', '', string.punctuation)

        for urim in mementos:

            logger.debug("examining memento {}".format(urim))
        
            memento = mementos[urim]
        
            if memento['processed_for_off_topic'] == True:
      
                logger.debug("memento {} has not been excluded from processing"
                    .format(urim))

                filename = memento['text-only_filename']
        
                with open(filename) as f:
                    filedata = f.read().lower()
                    filedata = filedata.translate(translator)
        
                if len(filedata) == 0:
                    logger.warning("there is no file data for urim {} "
                        "whose contents are stored in {}".format(
                        urim, filename))
                else:
                    filesdata.append(filedata)
                    urims.append(urim)
                    filenames.append(filename)

            else:
                logger.debug("not processing memento at URI-M {}"
                    " for off topic".format(urim))
                    
                logger.debug("discovered {} mementos for processing under"
                    " cosine similarity".format(len(filesdata)))
                
        if len(urims) > 0:
        
            logger.debug("we have {} URI-Ms for processing".format(len(urims)))
        
            first = urims.index(first_urim)
        
            tfidf_matrix = tfidf.fit_transform(filesdata)
        
            logger.debug("matrix: {}".format(tfidf_matrix.todense()))
        
            csresults = cosine_similarity(tfidf_matrix[first], tfidf_matrix)
        
            for i in range(0, len(csresults[0])):
        
                urim = urims[i]
        
                logger.debug("processing memento {}".format(urim))
                mementos[urim].setdefault('measures', {})
                mementos[urim]['measures']['cosine'] = csresults[0][i]
                logger.debug("memento {} should now have scores {}".format(urim,
                    mementos[urim]))
              
                if 'on-topic' not in mementos[urim]['measures']:
        
                    mementos[urim]['measures']['on_topic'] = True
        
                    if csresults[0][i] < self.threshold:
                        mementos[urim]['measures']['on_topic'] = False
                        mementos[urim]['measures']['off_topic_measure'] = \
                            'cosine'
        
                logger.debug("memento should now have on-topic score {}".format(mementos[urim]))

            return mementos

    def get_scores(self, input_filedata):

        tfidf = TfidfVectorizer(tokenizer=tokenize,
            stop_words=self.stopwords)

        updated_filedata = self.compute_scores_for_mementos_in_TimeMap(
            self.memento_scorefunction, input_filedata, tfidf)

        return updated_filedata

class JaccardDistanceAgainstSingleResource(TopicProcessor):

    def memento_scorefunction(self, mementos, first_urim, *args):

        logger.debug("there are {} mementos for processing"
            " under jaccard distance".format(len(mementos)))

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

        return mementos

    def get_scores(self, input_filedata):

        updated_filedata = self.compute_scores_for_mementos_in_TimeMap(
            self.memento_scorefunction, input_filedata)

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

    def memento_scorefunction(self, mementos, first_urim, *args):

        logger.debug("there are {} mementos for processing"
            " under TF Intersection".format(len(mementos)))

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

        return mementos

    def get_scores(self, input_filedata):

        updated_filedata = self.compute_scores_for_mementos_in_TimeMap(
            self.memento_scorefunction, input_filedata)

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
