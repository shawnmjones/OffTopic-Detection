import ntpath
import distance
import sys
import os
sys.path.append("source_code")
import off_topic_detector_cos_sim as ot

def compute_off_topic(old_uri_id, file_list, timemap_dict, collection_scores_file, threshold):

    vector_text = ot.build_vector_from_file_list(file_list)

    if vector_text is not None and len(vector_text) > 1:

        t0_text = vector_text[file_list[0]]
        t0_vector = ot.tokenize(t0_text)

        for filename in vector_text.keys():
            content_vector = ot.tokenize(vector_text[filename])
           
            jaccard_score = distance.jaccard(content_vector, t0_vector)

            computed_file_name = ntpath.basename(filename.replace('.txt', ''))
            mdatetime = computed_file_name
            memento_uri = timemap_dict[str(old_uri_id)][str(computed_file_name)] 

            collection_scores_file.write("{}\t{}\t{}\t{}\n".format(old_uri_id, mdatetime, memento_uri.strip(), jaccard_score))

            # Jaccard distance works differently than cosine similarity
#            if score > threshold:
#                memento_uri = timemap_dict[str(old_uri_id)][str(computed_file_name)]
#                off_topic_jaccard_file.write( str(score) + "\t" + memento_uri + "\n")
#            else:
#                new_timemap_file.write(old_uri_id+"\t"+str(computed_file_name)+"\t"+timemap_dict[str(old_uri_id)][str(computed_file_name)])
 

def get_off_topic_memento(timemap_file_name, collection_scores_file, collection_directory, threshold):

    timemap_dict = ot.convert_timemap_to_hash(timemap_file_name)

    timemap_list_file = open(timemap_file_name)

    print "Determining off-otpic mementos using Jaccard method."

    collection_scores_file.write("URIR_ID\tmemento_datetime\tmemento_uri\tjaccard_score\n")

    old_uri_id = "0"
    old_mem_id = "0"
    file_list = []

    for memento_record in timemap_list_file:
        fields = memento_record.split("\t")
        uri_id = fields[0]
        dt = fields[1]
        mem_id = fields[2]
        uri = fields[3]

        text_file = collection_directory + "/text/" + uri_id + "/" + dt + ".txt"

        if not os.path.isfile(text_file):
            continue

        if old_uri_id != uri_id and len(file_list) > 0:
            compute_off_topic(old_uri_id, file_list, timemap_dict, collection_scores_file, threshold)
            file_list = []

        file_list.append(text_file)
        old_uri_id = uri_id

    if len(file_list) > 0:
        compute_off_topic(old_uri_id, file_list, timemap_dict, collection_scores_file, threshold)
