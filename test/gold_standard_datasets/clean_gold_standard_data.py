import sys

def fix_urims_with_corrected_dates(filelines):

    newfilelines = []

    for line in filelines:
        uririd, mdt, urim, judgement = line.split('\t')

        if uririd != "id":

            mdt_in_urim = urim.replace('http://wayback.archive-it.org/', '') \
                                .split('/')[1]
    
            if mdt_in_urim != mdt:
                print("found mismatched memento-datetime in urim {},"
                    "where datetime {} does not match expected {}"
                    .format(urim, mdt_in_urim, mdt))
    
                urim = urim.replace(mdt_in_urim, mdt)

        newline = "\t".join([uririd, mdt, urim, judgement])

        newfilelines.append(newline)

    return newfilelines

if __name__ == '__main__':

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file) as f:
        filelines = f.readlines()

    improved_entries = fix_urims_with_corrected_dates(filelines)

    with open(output_file, 'w') as f:
        for line in improved_entries:
            f.write(line)
