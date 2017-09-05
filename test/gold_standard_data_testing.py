import sys
import os
import csv
from datetime import datetime

sys.path.append('../off_topic')

import topic_processor as tp
import memento_fetch as mf

def convert_gold_standard_data_to_dict(input_file):

    gold_standard_data = {}

    with open(input_file) as tsvfile:

        datareader = csv.reader(tsvfile, delimiter='\t')

        for row in datareader:
            if row[0] != 'id':
                urir_id = row[0]
                dt = row[1]
                urim = row[2].replace('/http', 'id_/http')
                ontopic = False

                if row[3] == "1":
                    ontopic = True

                mdatetime = datetime.strptime(dt, '%Y%m%d%H%M%S')

                urit = 'local-archive:timemap/{}'.format(urir_id)

                gold_standard_data.setdefault(urit, {}) 
                gold_standard_data[urit]['original'] = urir_id

                memento = {
                    'uri-m': urim,
                    'memento-datetime': mdatetime,
                    'gold-standard-ontopic': ontopic
                }

                gold_standard_data[urit].setdefault('mementos', []).append(memento)

    return gold_standard_data

def build_timemaps_from_gold_standard_data_dict(gold_standard_dict, timemap_dir):

    for urit in gold_standard_dict:

        with open("{}/metadata.tsv".format(timemap_dir), 'a', 1) as metadata_file:

            metadata_writer = csv.writer(metadata_file, delimiter='\t',
                quotechar='"', quoting=csv.QUOTE_ALL)

            mementos = []
            for memento in gold_standard_dict[urit]['mementos']:
                urim = memento['uri-m']
                mdt = memento['memento-datetime']

                mementos.append( (mdt, urim) )

            mementos.sort()

            urir = gold_standard_dict[urit]['original']

            from_date = mementos[0][0].strftime("%a, %d %b %Y %H:%M:%S GMT")
            until_date = mementos[-1][0].strftime("%a, %d %b %Y %H:%M:%S GMT")

            timemap_string = '<{}>; rel="original",\n'.format(urir)
            timemap_string += '<{}>; rel="self"; ' \
                'type="application/link-format"; ' \
                'from="{}"; until="{}",\n'.format(urit, from_date, until_date)

            memento_entries = []

            for i in range(len(mementos)):

                if i == 0 and i == len(mementos) - 1:
                    rel = "first last memento"

                elif i == 0:
                    rel = "first memento"

                elif i == len(mementos) - 1:
                    rel = "last memento"

                else:
                    rel = "memento"

                memento_datetime = mementos[i][0]
                urim = mementos[i][1]

                memento_entries.append('<{}>; rel="{}"; datetime="{}"'.format(
                    urim, rel, memento_datetime.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                        )
                    ))

            timemap_string += ',\n'.join(memento_entries)

            timemap_file = "{}/{}.dat".format(timemap_dir, urir)

            with open(timemap_file, 'w') as f:
                f.write(timemap_string)

            metadata_writer.writerow([urit, "200", urit, timemap_file, None])


if __name__ == '__main__':
    gold_standard_file = sys.argv[1]
    measure = sys.argv[2]
    working_directory = sys.argv[3]
    output_file = sys.argv[4]

    print("Starting processing of gold standard file {}"
        " using measure {}".format(gold_standard_file, measure))

    input_directory = None

    if len(sys.argv) > 5:
        input_directory = sys.argv[5]

    print("Loading Gold Standard data")
    gold_standard = convert_gold_standard_data_to_dict(gold_standard_file)

    if not input_directory:

        print("Preparing to download mementos based on Gold Standard data")
    
        memento_directory = "{}/mementos".format(working_directory)
        timemap_directory = "{}/timemaps".format(working_directory)
    
        if not os.path.isdir(memento_directory):
            os.makedirs(memento_directory)
    
        if not os.path.isdir(timemap_directory):
            os.makedirs(timemap_directory)
    
        print("building faux TimeMaps")
        build_timemaps_from_gold_standard_data_dict(gold_standard, timemap_directory) 
    
        print("downloading real raw mementos")
        for urit in gold_standard:
    
            urilist = []
            for memento in gold_standard[urit]['mementos']:
                urilist.append(memento['uri-m'])
    
            mf.download_uri_list(urilist, memento_directory)
    
    else:
        working_directory = input_directory
   
    print("parsing download metadata")
    input_data = mf.parse_downloads_into_structure(working_directory)

    print("computing scores") 
    threshold = tp.supported_measures[measure]['default_threshold']

    topic_processor = tp.get_topic_processor(measure, threshold)

    scoredata = topic_processor.get_scores(input_data)

    print("cross-referening scores and writing to {}".format(output_file))

    goldmementocount = 0

    with open(output_file, 'w') as tsvfile:

        outputwriter = csv.writer(tsvfile, delimiter='\t')
        processed_goldstandard_uris = []

        for urit in scoredata:

            print("processing TimeMap {}".format(urit))
    
            for urim in scoredata[urit]['mementos']:

                memento = scoredata[urit]['mementos'][urim]

                goldmementocount += 1

                print("processing memento {}".format(memento))

                try:
                    score = memento['measures'][measure]
                    swscore = memento['measures']['on_topic']

                except KeyError as e:
                    score = 'not calculated by topic processor'
                    swscore = 'not calculated by topic processor' 

                for gsmemento in gold_standard[urit]['mementos']:

                    if gsmemento['uri-m'] == urim:
                        goldscore = gsmemento['gold-standard-ontopic']
                        break

                outputwriter.writerow([urim, goldscore, measure, score, swscore])

                processed_goldstandard_uris.append(urim)

        for urit in gold_standard.keys():

            for memento in gold_standard[urit]['mementos']:

                urim = memento['uri-m']

                if urim not in processed_goldstandard_uris:
                    goldscore = memento['gold-standard-ontopic']
                    outputwriter.writerow([urim, goldscore, measure, 'MISSING', 'MISSING'])

    print("Status report:")

    processed_count = 0
    unsupported_format_count = 0 
    no_content_type_count = 0
    content_size_zero_count = 0
    unknown_process_status_count = 0
    urimcount = 0
    
    for urit in scoredata:

        for urim in scoredata[urit]['mementos']:
            urimcount += 1

            memento = scoredata[urit]['mementos'][urim]

            process_status = memento['processed_for_off_topic']

            if process_status == True:
                processed_count += 1
            elif 'unsupported file format' in process_status:
                unsupported_format_count += 1
            elif 'no content-type header for memento' in process_status:
                no_content_type_count += 1
            elif 'content size is zero for memento' in process_status:
                content_size_zero_count += 1
            else:
                unknown_process_status_count += 1

    print("URI-Ms in gold standard data: {}".format(goldmementocount))
    print("All URI-Ms in data structure: {}".format(urimcount))
    print("Should be processed: {}".format(processed_count))
    print("Unsupported format: {}".format(unsupported_format_count))
    print("No Content Type header: {}".format(no_content_type_count))
    print("Content size zero: {}".format(content_size_zero_count))
    print("Unknown processing status: {}".format(unknown_process_status_count))
        
    
    print("Done with processing, output data is in {}".format(output_file))
