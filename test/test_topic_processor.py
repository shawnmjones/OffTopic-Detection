import unittest
import sys
import os
import shutil
import logging
import pprint

sys.path.append('../off_topic')
import  datetime
import topic_processor as tp

logging.basicConfig(level=logging.DEBUG)

# this is useful for debugging at times
pp = pprint.PrettyPrinter(indent=4)

working_dir = '/tmp/test_topic_processor'

class TestErrorStates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        #logger = logging.getLogger(__name__)
        #tp.logger = logger

        if not os.path.isdir(working_dir):
            os.makedirs(working_dir)

        # in case we have something leftover from a previous run
        if os.path.isdir('{}/samplecontent'.format(working_dir)):
            shutil.rmtree(working_dir)
        
        shutil.copytree('samplecontent', "{}/samplecontent".format(working_dir))

    @classmethod
    def tearDownClass(cls):

        shutil.rmtree(working_dir)
         

    def test_empty_filedata(self):

        measures = {
            'cosine': tp.CosineSimilarityAgainstTimeMap(
                tp.supported_measures['cosine']['default_threshold']),

            'bytecount': tp.ByteCountAgainstSingleResource(
                tp.supported_measures['bytecount']['default_threshold']),

            'jaccard': tp.JaccardDistanceAgainstSingleResource(
                tp.supported_measures['jaccard']['default_threshold']),

            'tfintersection': tp.TFIntersectionAgainstSingleResource(
                tp.supported_measures['tfintersection']['default_threshold']),

            'wordcount': tp.WordCountAgainstSingleResource(
                tp.supported_measures['wordcount']['default_threshold'])
                }

        def test_each_measure(instance):
            self.assertEqual(instance.get_scores(None), None)

        for measure in measures:
            test_each_measure(measures[measure])

    def test_oneEmptyVocabulary(self):

        measures = {
            'cosine': tp.CosineSimilarityAgainstTimeMap(
                tp.supported_measures['cosine']['default_threshold']),

            'bytecount': tp.ByteCountAgainstSingleResource(
                tp.supported_measures['bytecount']['default_threshold']),

            'jaccard': tp.JaccardDistanceAgainstSingleResource(
                tp.supported_measures['jaccard']['default_threshold']),

            'tfintersection': tp.TFIntersectionAgainstSingleResource(
                tp.supported_measures['tfintersection']['default_threshold']),

            'wordcount': tp.WordCountAgainstSingleResource(
                tp.supported_measures['wordcount']['default_threshold'])
                }

        filedata = {
            'test': {
                'mementos': [
                    {
                        'uri-m': 'local-archive:test1',
                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                        'content_filename': '{}/samplecontent/verysimple.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                    },
                    {
                        'uri-m': 'local-archive:test1',
                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                        'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                    }
                ]
            }
        }

        def test_each_measure(instance, filedata):
            outdata = instance.get_scores(filedata) 

            self.assertTrue(outdata['test']['mementos'][0]['measures']['on_topic'])
            self.assertFalse(outdata['test']['mementos'][1]['measures']['on_topic'])

        for measure in measures:
            test_each_measure(measures[measure], filedata)
        
    def test_exactSameContent(self):

        measures = {
            'cosine': tp.CosineSimilarityAgainstTimeMap(
                tp.supported_measures['cosine']['default_threshold']),

            'bytecount': tp.ByteCountAgainstSingleResource(
                tp.supported_measures['bytecount']['default_threshold']),

            'jaccard': tp.JaccardDistanceAgainstSingleResource(
                tp.supported_measures['jaccard']['default_threshold']),

            'tfintersection': tp.TFIntersectionAgainstSingleResource(
                tp.supported_measures['tfintersection']['default_threshold']),

            'wordcount': tp.WordCountAgainstSingleResource(
                tp.supported_measures['wordcount']['default_threshold'])
                }


        filedata = {
            'test': {
                'mementos': [
                    {
                        'uri-m': 'local-archive:test1',
                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                        'content_filename': '{}/samplecontent/verysimple.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                    },
                    {
                        'uri-m': 'local-archive:test2',
                        'memento-datetime': datetime.datetime(2011, 2, 2, 2, 3, 26),
                        'content_filename': '{}/samplecontent/verysimple_same.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                    }
                ]
            }
        }

        def test_each_measure(instance, filedata):
            outdata = instance.get_scores(filedata) 

            self.assertTrue(outdata['test']['mementos'][0]['measures']['on_topic'])
            self.assertTrue(outdata['test']['mementos'][1]['measures']['on_topic'])


        for measure in measures:
            test_each_measure(measures[measure], filedata)

    def test_only1MementoAndItsEmpty(self):

        measures = {
            'cosine': tp.CosineSimilarityAgainstTimeMap(
                tp.supported_measures['cosine']['default_threshold']),

            'bytecount': tp.ByteCountAgainstSingleResource(
                tp.supported_measures['bytecount']['default_threshold']),

            'jaccard': tp.JaccardDistanceAgainstSingleResource(
                tp.supported_measures['jaccard']['default_threshold']),

            'tfintersection': tp.TFIntersectionAgainstSingleResource(
                tp.supported_measures['tfintersection']['default_threshold']),

            'wordcount': tp.WordCountAgainstSingleResource(
                tp.supported_measures['wordcount']['default_threshold'])
                }

        filedata = {
            'test': {
                'mementos': [
                    {
                        'uri-m': 'local-archive:test1',
                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                        'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                    }
                ]
            }
        }

        def test_each_measure(instance, filedata):
            outdata = instance.get_scores(filedata) 

            self.assertTrue(outdata['test']['mementos'][0]['measures']['on_topic'])
            self.assertEqual(outdata['test']['mementos'][0]['measures']['off_topic_measure'],
                'only 1 memento')

        for measure in measures:
            test_each_measure(measures[measure], filedata)

    def test_mark_unsupported_items_supported_content_type_html(self):

        filedata = {
            'test': {
                'mementos': [
                    {
                        'uri-m': 'local-archive:test1',
                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                        'content_filename': '{}/samplecontent/facebook_example.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/facebook_example.hdr'.format(working_dir)
                    }
                ]
            }
        }

        outdata = tp.mark_unsupported_items(filedata)

        self.assertEqual(outdata['test']['mementos'][0]['content-type'], 'text/html;charset=utf-8')
        self.assertTrue(outdata['test']['mementos'][0]['processed_for_off_topic'])

#    def test_mark_unsupported_items_unsupported_content_type_jpg(self):
#
#        filedata = {
#            'test': {
#                'mementos': [
#                    {
#                        'uri-m': 'local-archive:test1',
#                        'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
#                        'content_filename': '{}/samplecontent/facebook_example.dat'.format(working_dir),
#                        'headers_filename': '{}/samplecontent/facebook_example.hdr'.format(working_dir)
#                    }
#                ]
#            }
#        }
#
#        outdata = tp.mark_unsupported_items(filedata)
#
#        self.assertEqual(outdata['test']['mementos'][0]['content-type'], 'text/html;charset=utf-8')
#        self.assertFalse(outdata['test']['mementos'][0]['processed_for_off_topic'])
