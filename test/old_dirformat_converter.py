import sys
import os
import shutil

sys.path.append('../off_topic')
import memento_fetch as mf

newformatdir = sys.argv[1]
oldformatdir = sys.argv[2]

tmfilename = "{}/timemap.txt".format(oldformatdir)
seedlistfilename = "{}/seed_list.txt".format(oldformatdir)

if not os.path.isdir(oldformatdir):
    os.makedirs(oldformatdir)

htmldir = "{}/html".format(oldformatdir)

if not os.path.isdir(htmldir):
    os.makedirs(htmldir)

with open(tmfilename, 'w') as tmfile:

    with open(seedlistfilename, 'w') as seedlist:

        data = mf.parse_downloads_into_structure(newformatdir)
    
        uritcount = 0
    
        for urit in data:

            print("processing URI-T: {}".format(urit))

            uritcount += 1
    
            urimcount = 0

            htmldir = "{}/html/{}".format(oldformatdir, uritcount)

            if not os.path.isdir(htmldir):    
                os.makedirs(htmldir)

            seedlistset = []
    
            for urim in data[urit]['mementos']:
                urimcount += 1
                print("processing URI-M: {}".format(urim))
                collection, mdt, urir = urim.replace("http://wayback.archive-it.org/", '').split('/', 2)

                if 'id_' in mdt:
                    mdt = mdt.replace('id_', '')
        
                # write out timemap.txt
                tmfile.write("{}\t{}\t{}\t{}\n".format(uritcount, mdt, urimcount, urim))

                contentfilename = data[urit]['mementos'][urim]['content_filename']
                destfilename = "{}/{}.html".format(htmldir, mdt)

                shutil.copyfile(contentfilename, destfilename)

                seedlistset.append( (uritcount, urir) )

            seedlistset = set(seedlistset)

            for item in seedlistset:
                seedlist.write("{}\t{}\n".format(item[0], item[1]))
