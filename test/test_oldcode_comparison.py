import unittest
import sys
import os
import shutil
import logging
import pprint
import csv

sys.path.append('../off_topic')
import  datetime
import topic_processor as tp

#logging.basicConfig(level=logging.DEBUG)

# this is useful for debugging at times
pp = pprint.PrettyPrinter(indent=4)

#working_dir = '/tmp/test_topic_processor'
oldcode_scoredata = {}
example_mementodata = {}

class TestOldCodeComparison(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        with open('test_data_from_original/off_topic_run-gs1068-defaults-20170917162505.out') \
            as f:

            for line in f:
                line = line.strip()

                if "Similarity" not in line:
                    if line != '':

                        score, urim = line.split('\t')

                        oldcode_scoredata.setdefault('1068', {})
                        oldcode_scoredata['1068'][urim] = score

        collection = '1068'
        example_mementodata.setdefault(collection, {})
        collection_directory = "{}/test_data_from_original/collection_gs{}".format(
            os.getcwd(), collection)

        with open("{}/timemap.txt".format(collection_directory)) as f:

            for line in f:

                line = line.strip()

                uririd, mdt, urimid, urim = line.split('\t')
    
                tm_uri = 'local-archive:test{}'.format(uririd)
    
                example_mementodata[collection].setdefault(tm_uri, {})
    
                content_filename = "{}/html/{}/{}.html".format(
                    collection_directory, uririd, mdt)
    
                example_mementodata[collection][tm_uri].setdefault('mementos', {})
                example_mementodata[collection][tm_uri]['mementos'].setdefault(urim, {})

                example_mementodata[collection][tm_uri]['mementos'][urim]['content_filename'] = content_filename
                example_mementodata[collection][tm_uri]['mementos'][urim]['headers_filename'] = \
                    "{}/samplecontent/verysimple.hdr".format(os.getcwd())
                example_mementodata[collection][tm_uri]['mementos'][urim]['memento-datetime'] = \
                    datetime.datetime.strptime(mdt, '%Y%m%d%H%M%S')

    @classmethod
    def tearDownClass(cls):

        pass


    def test_collection_scores(self):

        def convert_results(results):

            scoredata = {}

            for urit in results:

                for urim in results[urit]['mementos']:

                    print(urim)

                    try:
                        score = results[urit]['mementos'][urim]['measures']['cosine']
                    except KeyError as e:
                        print(e)
                        score = None

                    scoredata[urim] = score 

            return scoredata

        csat = tp.CosineSimilarityAgainstTimeMap(
            tp.supported_measures['cosine']['default_threshold'])

        results_1068 = csat.get_scores(example_mementodata["1068"])

        converted_results_1068 = convert_results(results_1068)

        for collection in oldcode_scoredata:
            print("working on collection {}".format(collection)) 
            for urim in oldcode_scoredata[collection]:
                self.assertAlmostEqual(converted_results_1068[urim], 
                    oldcode_scoredata[urim])


