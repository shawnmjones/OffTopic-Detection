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

working_dir = '/tmp/test_topic_processor'

class TestErrorStates(unittest.TestCase):

    measures = {
        'cosine': {
            'default_instance': tp.CosineSimilarityAgainstTimeMap(
                tp.supported_measures['cosine']['default_threshold']),
            'same_score': 1.0
            },
    
        'bytecount': {
            'default_instance': tp.ByteCountAgainstSingleResource(
                tp.supported_measures['bytecount']['default_threshold']),
            'same_score': 0.0
            },
    
        'jaccard': {
            'default_instance': tp.JaccardDistanceAgainstSingleResource(
                tp.supported_measures['jaccard']['default_threshold']),
            'same_score': 0.0
            },
    
        'wordcount': {
            'default_instance': tp.WordCountAgainstSingleResource(
                tp.supported_measures['wordcount']['default_threshold']),
            'same_score': 0.0
            },

        'tfintersection': {
            'default_instance': tp.TFIntersectionAgainstSingleResource(
                tp.supported_measures['tfintersection']['default_threshold']),
            'same_score': 0.0
            },
    
    }

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

    def sanity_check(self, instance, measure, filedata):

        outdata = instance.get_scores(filedata) 
        
        for urit in filedata:
            try:
                tm = outdata[urit]
            except KeyError:
                self.fail("Measure {}: "
                    "TimeMap key {} missing from output data structure".format(
                    measure, urit))
        
            try:
                mementos = tm['mementos']
            except KeyError:
                self.fail("Measure {}: "
                    "Mementos key missing from output data structure for "
                    "TimeMap {}".format(measure, urit))
        
            expected_mementos = filedata[urit]['mementos']
        
            for urim in expected_mementos:
        
                try:
                    memento = mementos[urim]
                except KeyError:
                    self.fail("Measure {}: "
                        "Memento {} missing from output data structure for "
                        "TimeMap {}".format(measure, urim, urit))
                except TypeError:
                    self.fail("Measure {}: "
                        "Mementos list expected to contain {} is set to None "
                        "from output data structure for "
                        "TimeMap {}".format(measure, urim, urit))
        
                try:
                    measures = memento['measures']
                except KeyError:
                    self.fail("Measure {}: "
                        "Measures missing from memento {} from output "
                        "data structure for TimeMap {}".format(measure, urim, urit))

    def test_empty_filedata(self):

        def test_each_measure(instance):
            self.assertEqual(instance.get_scores(None), None)

        for measure in self.measures:
            test_each_measure(self.measures[measure]['default_instance'])

    def test_oneEmptyVocabulary(self):

        filedata = {
            'test': {
                'mementos': {
                        'local-archive:test1': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/verysimple.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                        },
                        'local-archive:test2': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                        }
                }
            }
        }

        def test_each_measure(instance, filedata):
            self.sanity_check(instance, measure, filedata)

            outdata = instance.get_scores(filedata) 

            self.assertTrue(outdata['test']['mementos']['local-archive:test1']['measures']['on_topic'])
            self.assertIsNone(outdata['test']['mementos']['local-archive:test2']['measures']['on_topic'])

        for measure in self.measures:
            test_each_measure(self.measures[measure]['default_instance'], filedata)

    def test_allEmptyVocabulary(self):

        filedata = {
            'local-archive:test': {
                'mementos': {
                        'local-archive:test1': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                        },
                        'local-archive:test2': {
                            'memento-datetime': datetime.datetime(2011, 2, 2, 2, 3, 26),
                            'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                        }
                }
            }
        }

        def test_each_measure(instance, measure, filedata):

            self.sanity_check(instance, measure, filedata)

            outdata = instance.get_scores(filedata) 

            self.assertIsNone(outdata['local-archive:test']['mementos']['local-archive:test1']['measures']['on_topic'], 
                msg="measure {} did not work".format(measure))

            self.assertIsNone(outdata['local-archive:test']['mementos']['local-archive:test2']['measures']['on_topic'],
                msg="measure {} did not work".format(measure))

        for measure in self.measures:
            test_each_measure(self.measures[measure]['default_instance'], measure, filedata)


    def test_exactSameContent(self):

        filedata = {
            'test': {
                'mementos': {
                        'local-archive:test1': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/verysimple.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                        },
                        'local-archive:test2': {
                            'memento-datetime': datetime.datetime(2011, 2, 2, 2, 3, 26),
                            'content_filename': '{}/samplecontent/verysimple_same.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/verysimple.hdr'.format(working_dir)
                        }
                }
            }
        }

        def test_each_measure(instance, filedata, measure):
            self.sanity_check(instance, measure, filedata)

            outdata = instance.get_scores(filedata) 

            mementos = outdata['test']['mementos']

            self.assertTrue(mementos['local-archive:test1']['measures']['on_topic'])
            self.assertTrue(mementos['local-archive:test2']['measures']['on_topic'])

            # pesky floats
            self.assertAlmostEqual(mementos['local-archive:test1']['measures'][measure],
                self.measures[measure]['same_score'],
                msg="Measure {} did not produce the correct score for "
                "two equal documents.".format(measure))


        for measure in self.measures:
            test_each_measure(self.measures[measure]['default_instance'], filedata, measure)

    def test_only1MementoAndItsEmpty(self):

        filedata = {
            'test': {
                'mementos': {
                        'local-archive:test1': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/empty_vocab.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/empty_vocab.hdr'.format(working_dir)
                        }
                }
            }
        }

        def test_each_measure(instance, filedata, measure):

            self.sanity_check(instance, measure, filedata)

            outdata = instance.get_scores(filedata) 

            self.assertTrue(outdata['test']['mementos']['local-archive:test1']['measures']['on_topic'])
            self.assertEqual(outdata['test']['mementos']['local-archive:test1']['measures']['off_topic_measure'],
                'only 1 memento')

        for measure in self.measures:
            test_each_measure(self.measures[measure]['default_instance'], filedata, measure)

    def test_mark_unsupported_items_supported_content_type_html(self):

        filedata = {
            'test': {
                'mementos': {
                        'local-archive:test1': {
                            'memento-datetime': datetime.datetime(2011, 2, 1, 2, 3, 26),
                            'content_filename': '{}/samplecontent/facebook_example.dat'.format(working_dir),
                            'headers_filename': '{}/samplecontent/facebook_example.hdr'.format(working_dir)
                        }
                }
            }
        }

        outdata = tp.mark_unsupported_items(filedata)

        self.assertEqual(outdata['test']['mementos']['local-archive:test1']['content-type'], 'text/html;charset=utf-8')
        self.assertTrue(outdata['test']['mementos']['local-archive:test1']['processed_for_off_topic'])

    def test_process_arabic_with_cosine(self):
        """
            In this set, there were 2 mementos, 1 did not get processed. Why?
        """


        filedata = {
            'test': {
                'mementos': {
                    'local-archive:test1': {
                        'memento-datetime': datetime.datetime(2012, 5, 6, 15, 29, 19),
                        'content_filename': '{}/samplecontent/not_processed1-1.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/not_processed1-1.hdr'.format(working_dir)
                    },
                    'local-archive:test2': {
                        'memento-datetime': datetime.datetime(2012, 5, 24, 10, 36, 23),
                        'content_filename': '{}/samplecontent/not_processed1-2.dat'.format(working_dir),
                        'headers_filename': '{}/samplecontent/not_processed1-2.hdr'.format(working_dir)
                    }
                }
            }
        }

        
        csat = tp.CosineSimilarityAgainstTimeMap(0.15)

        self.sanity_check(csat, 'cosine', filedata)

    def test_originally_not_processed_by_cosine2(self):

        test_working_dir = "{}/samplecontent/ahram.org.eg".format(working_dir)

        def process_ahram_mementos(metadata_filename):

            mementos = {}

            with open(metadata_filename) as metadata_file:
                csvreader = csv.reader(metadata_file, delimiter='\t', quotechar='"')

                for row in csvreader:
                    urim = row[0]
                    status = row[1]
                    urim_redir = row[2]
                    content_file = row[3]
                    header_file = row[4]

                    mdt = datetime.datetime.strptime(
                        urim.split('/')[4].replace('id_', ''),
                        "%Y%m%d%H%M%S")

                    memento = {}
                    memento['memento-datetime'] = mdt
                    memento['content_filename'] = "{}/mementos/{}".format(test_working_dir, content_file)
                    memento['headers_filename'] = "{}/mementos/{}".format(test_working_dir, header_file)

                    mementos[urim] = memento
                    
            return mementos


        filedata = {

            'test': {
                'mementos': {}
                }
        }

        filedata['test']['mementos'] = process_ahram_mementos(
                    "{}/mementos/metadata.tsv".format(test_working_dir))

        csat = tp.CosineSimilarityAgainstTimeMap(0.15)

        self.sanity_check(csat, 'cosine', filedata)

