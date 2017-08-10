import sys
import logging
import argparse
from input_types import supported_input_types, get_input_type

supported_measures = {
    'cosine': {
        'name': 'Cosine Similarity',
        'default_threshold': 0.15
    },
    'jaccard': {
        'name': 'Jaccard Distance',
        'default_threshold': 0.10
    },
    'wcount': {
        'name': 'Word Count',
        'default_threshold': -0.10
    }
}

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
            "for a list of URIs, use something like (no spaces between commas)\n"
            "-i uris=http://example.com,http://example2.com\n\n"
            "for an Archive-It collection use something like\n"
            "-i archiveit=3639\n\n"
            "for a WARC use\n"
            "-i warc=myfile.warc.gz\n\n"
            "for a TimeMap use\n"
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
        "* warc=[warc-filename]\n"
        "* archiveit=[collection identifier or collection URI]\n"
        "* timemap=[URI of TimeMap]\n"
        "* uris=[list of URIs separated by commas with no spaces]\n"
        "* dir=[existing input directory from prior run]"
        )

    parser.add_argument('-o', '--output', dest='output_filename', 
        type=str, required=True,
        help="file name in which to store the scores")

    parser.add_argument('-d', '--directory', dest='working_directory',
        default='/tmp/working', type=str,
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
        default=sys.stdout, type=str,
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
  
    print("verbose: {}".format(verbose))

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
    logger.debug('args: {}'.format(args))

    # TODO: submit input_type to a factory method and get back an object that
    # handles that input type
    input_data = get_input_type(args.input_type[0], args.input_type[1],
        logger)
    input_filelist = input_data.get_filelist()

    # TODO: submit directory output from input_type to a topic processor

    # TODO: write output to a file

    logger.info('Finishing run')
