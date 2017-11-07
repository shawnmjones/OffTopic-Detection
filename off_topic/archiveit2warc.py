import sys
import logging
import logging.config
import argparse

from warc_conversion_input_types import supported_input_types

def process_input_types(input_argument):

    if '=' not in input_argument:
        raise argparse.ArgumentTypeError(
            "no required argument supplied for input type {}\n\n"
            "Examples:\n"
            "for an Archive-It collection use something like\n"
            "-i archiveit=3639\n\n"
            "for a TimeMap use (separate with commas, but not spaces)\n"
            "-i timemap=http://archive.example.org/timemap/http://example.com"
            .format(input_argument)
            )

    input_type, argument = input_argument.split('=') 

    if input_type not in supported_input_types:
        raise argparse.ArgumentTypeError(
            "{} is not a supported input type, supported types are {}".format(
                input_type, list(supported_input_types.keys()))
            )

    if ',' in argument:
        arguments = argument.split(',')
    else:
        arguments = [ argument ]

    return input_type, arguments

def process_arguments(args):

    parser = argparse.ArgumentParser(prog="python {}".format(args[0]),
        description="Converts Archive-It Collection Seeds Into WARC",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-i', '--input', dest='input_type',
        required=True, type=process_input_types,
        help="input data to use with one of the following:\n"
        "* archiveit=[collection identifier or collection URI]\n"
        "* timemap=[URI of TimeMap]\n"
        "* dir=[existing working directory from prior run]"
        )

    parser.add_argument('-d', '--directory', dest='working_directory',
        default='/tmp/working',
        help="The working directory holding data being downloaded"
        " and processed.")

#    parser.add_argument('-l', '--logfile', dest='logfile',
#        default=sys.stdout,
#        help="path to logging file")

    parser.add_argument('-o', '--output-directory', dest='output_directory',
        required=True,
        help="The directory the WARCs will be written to.")

    parser.add_argument('-v', '--verbose',
        action='store_true',
        help="raise the logging level to debug for more verbose output")

    return parser.parse_args()

if __name__ == '__main__':

    logging.config.fileConfig('logging.ini')
    logger = logging.getLogger(__name__)

    logger.info("Starting")

    args = process_arguments(sys.argv)

    logger.info("Using input type of {} with argument {}".format(
        args.input_type[0], args.input_type[1]) )

    logger.info("Using working directory of {}".format(
        args.working_directory) )

    logger.info("Using output directory of {}".format(
        args.output_directory) )

    input_type = get_input_type(args.input_type[0], args.input_type[1])
    input_type.write_WARCs(args.working_directory, args.output_directory) 

    logger.info("Finished, WARCs have been written to {}".format(
        args.output_directory) )

    logger.info("finished execution")
