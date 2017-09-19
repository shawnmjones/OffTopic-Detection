import sys

goldstandard_file = sys.argv[1]
output_file = sys.argv[2]

with open(goldstandard_file) as f:

    with open(output_file, 'w') as g:

        old_uririd = -1
        memento_count = 1

        for line in f:

            if line[0:2] != 'id':

                line = line.strip()
    
                uririd, mdt, urim, label = [ str(i) for i in line.split('\t') ]
    
                if uririd == old_uririd: 
                    memento_count += 1
                else:
                    memento_count = 1
                    old_uririd = uririd
    
                g.write('\t'.join( [ uririd, mdt, str(memento_count), urim ] ) ) 
                g.write('\n')
