import re
import urllib2
from sys import argv
import sys
import time
import os
import os.path

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
         collection_id = sys.argv[1]
    else:
         print "\nUsage get_off_topic_using_cosine_similarity [collection_id]"
         print "collection_id: is the id of the collection as it appears on ArchiveIt"
         sys.exit(1)
 
         
    collection_directory = "data/collection_"+str(collection_id)
    timemap_file=open(collection_directory+"/timemap.txt")
    
    number_of_mementos = 0
    for memento_record in timemap_file:
        number_of_mementos = number_of_mementos + 1
    timemap_file.close()
    
    timemap_file=open(collection_directory+"/timemap.txt")
    
    number_of_downloading_mementos = 1
    for memento_record in timemap_file:

        fields = memento_record.split("\t")
        uri_id = fields[0]
        dt = fields[1]
        mem_id = fields[2]
        uri = fields[3]
        print "Downloading "+str(number_of_downloading_mementos)+" out of "+str(number_of_mementos)+" with uri: "+uri
        
        if int(uri_id) < 0:
            continue
        uri = uri.replace(dt,dt+"id_")
        try:
            ensure_dir(collection_directory+"/html/"+uri_id+"/")
            memento_file_name = collection_directory+"/html/"+uri_id+"/"+dt+".html"
            if os.path.exists(memento_file_name) :
                print "found"
                continue
            else:
                print memento_file_name

            request = urllib2.Request(uri)
            opener = urllib2.build_opener()
            response = opener.open(request)

            the_page = response.read()
            response.close();
            
            f = open(memento_file_name,"w")
            f.write(the_page)
            f.close()
        except urllib2.HTTPError, e:    
            print str(e.code) +"\n"+str(e.msg)+"\n"+str(e.args)
        except urllib2.URLError, e:
            print str(e.args)+"\n"+str(e.reason)+"\n"+str(e.args)
        time.sleep(2)
        number_of_downloading_mementos=number_of_downloading_mementos+1
