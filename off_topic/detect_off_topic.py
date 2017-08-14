import sys
import logging
import argparse
from input_types import supported_input_types, get_input_type
from topic_processor import supported_measures, get_topic_processor

import pprint
pp = pprint.PrettyPrinter(indent=4)

def process_similarity_measure_inputs(input_argument):
    
    input_measures = input_argument.split(',')

    measures_used = {}

    for measure in input_measures:

        try:
            if '=' in measure:
                measure_name, threshold = measure.split('=')
                
                if measure_name not in supported_measures:
                    raise argparse.ArgumentTypeError(
                        "measure '{}' is not supported at this time".format(
                            measure_name)
                            )

                measures_used[measure_name] = threshold

            else:
                measures_used[measure] = \
                    supported_measures[measure]['default_threshold']
        except KeyError:
            raise argparse.ArgumentTypeError(
                "measure '{}' is not supported at this time".format(
                    measure
                    )
                )

    return measures_used

def process_input_types(input_argument):

    if '=' not in input_argument:
        raise argparse.ArgumentTypeError(
            "no required argument supplied for input type {}\n\n"
            "Examples:\n"
            "for an Archive-It collection use something like\n"
            "-i archiveit=3639\n\n"
            "for WARCs use (separate with commas, but no spaces)\n"
            "-i warc=myfile.warc.gz,myfile2.warc.gz\n\n"
            "for a TimeMap use (separate with commas, but not spaces)\n"
            "-i timemap=http://archive.example.org/timemap/http://example.com"
            .format(input_argument)
            )

    input_type, argument = input_argument.split('=') 

    if input_type not in supported_input_types:
        raise argparse.ArgumentTypeError(
            "{} is not a supported input type, supported types are {}".format(
                input_type, supported_input_types)
            )

    if ',' in argument:
        arguments = argument.split(',')
    else:
        arguments = [ argument ]

    return input_type, arguments
        

def process_arguments(args):

    parser = argparse.ArgumentParser(prog="python {}".format(args[0]),
        description='Detecting off-topic webpages.',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-i', '--input', dest='input_type',
        required=True, type=process_input_types,
        help="input data to use with one of the following:\n"
        "* warc=[warc-filenames separated by commas with no spaces]\n"
        "* archiveit=[collection identifier or collection URI]\n"
        "* timemap=[URI of TimeMap]\n"
        "* dir=[existing input directory from prior run]"
        )

    parser.add_argument('-o', '--output', dest='output_filename', 
        required=True, help="file name in which to store the scores")

    parser.add_argument('-d', '--directory', dest='working_directory',
        default='/tmp/working',
        help='The working directory holding the data being downloaded'
        ' and processed.')

    measurehelp = ""
    for measure in supported_measures:
        measurehelp += "* {} - {}, default threshold {}\n".format(
            measure, supported_measures[measure]['name'],
            supported_measures[measure]['default_threshold'])

    parser.add_argument('-m', '--measures', dest='measures',
        default="cosine=0.15,wcount=0.10",
        type=process_similarity_measure_inputs,
        help="similarity measures to use, separated by commas with no spaces\n"
        "with thresholds after (e.g., jaccard=0.10,cosine=0.15,wcount);\n"
        "leave thresholds off to use default thresholds;\n"
        "accepted values:\n{}".format(measurehelp)
        )

    parser.add_argument('-l', '--logfile', dest='logfile',
        default=sys.stdout,
        help="path to logging file")

    parser.add_argument('-v', '--verbose', dest='verbose',
        action='store_true',
        help="raise the logging level to debug for more verbose output")

    return parser.parse_args()

def get_logger(appname, loglevel, logfile):
    logger = logging.getLogger(appname)
    logger.setLevel(logging.DEBUG)

    # shamelessly stolen from logging HOWTO
    if logfile == sys.stdout:
        ch = logging.StreamHandler()
    else:
        ch = logging.FileHandler(logfile)

    ch.setLevel(loglevel)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

def calculate_loglevel(verbose):
  
    if verbose:
        return logging.DEBUG
    else:
        return logging.INFO
          

if __name__ == '__main__':

    args = process_arguments(sys.argv)

    # set up logging for the rest of the system
    logger = get_logger(__name__, calculate_loglevel(args.verbose), 
        args.logfile)

    logger.info('Starting run')
    logger.info('args: {}'.format(args))

    input_data = get_input_type(args.input_type[0], args.input_type[1],
        args.working_directory, logger)
    input_filedata = input_data.get_filedata()
    logger.info('input filedata now contains {} entries'.format(
        len(input_filedata)))
    logger.debug('using input_filelist: {}'.format(input_filedata))

    scores = None
    # TODO: submit directory output from input_type to a topic processor
    for measure in args.measures:
        topic_processor = get_topic_processor(measure, 
            args.measures[measure], args.working_directory, logger)
        scores = topic_processor.get_scores(input_filedata, scores)

    # TODO: write output to a file

    with open(args.output_filename, 'w') as f:

        for urit in scores:

            for memento in scores[urit]['mementos']:

                if memento['measures']['on_topic'] == False:
                    urim = memento['uri-m']
                    off_topic_measure = memento['measures']['off_topic_measure']
                    score = memento['measures'][off_topic_measure]

                    f.write("{}\t{}\t{}\n".format(
                        score, off_topic_measure, urim))

    logger.info('Finishing run')
