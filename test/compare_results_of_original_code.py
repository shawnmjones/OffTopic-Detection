import sys
import csv

goldstandard_filename = sys.argv[1]
original_tool_output_filename = sys.argv[2]
measure = sys.argv[3]
outputfile = sys.argv[4]

tool_offtopic = {}
goldstandard = {}

with open(original_tool_output_filename) as tooldata:

    linecount = 0

    for line in tooldata:

        print("processing tool output line: {}".format(line))

        line = line.strip()
        
        if line[0:10] != 'Similarity':
            if line != '':
                (score, urim) = line.split('\t')
    
                if 'id_/http' in urim:
                    urim = urim.replace('id_/http', '/http')
  
                print("saving score for off-topic URI-M: {}".format(urim))

                tool_offtopic[urim] = score

        linecount +=1

    print("number of off-topic URI-Ms: {}".format(len(tool_offtopic)))
    print("number of lines in tool output: {}".format(linecount))


with open(goldstandard_filename) as golddata:

    linecount = 0

    for line in golddata:

        line = line.strip()

        print("processing goldstandard line: {}".format(line))
        
        if line [0:2] != 'id':
            uid, mdt, urim, ontopic = line.split('\t')

            if ontopic == '1':
                ontopic = True
            else:
                ontopic = False

            goldstandard[urim] = ontopic

        linecount +=1

    print("number of URI-Ms: {}".format(len(goldstandard)))
    print("number of lines in gold standard file: {}".format(linecount))

with open(outputfile, 'w') as tsvfile:

    outputwriter = csv.writer(tsvfile, delimiter='\t')

    for urim in goldstandard:

        print("processing URI-M {} from goldstandard".format(urim))
    
        goldscore = goldstandard[urim]
    
        swscore = True
        score = 'match'
    
        if urim in tool_offtopic:
            print("found URI-M in off-topic output")
            swscore = False
            score = tool_offtopic[urim]
    
        outputwriter.writerow([urim, goldscore, measure, score, swscore])
