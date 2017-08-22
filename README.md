
This system evaluates a series of mementos (archived web pages) to determine which are off topic. The series can be part of an Archive-It collection, a single TimeMap, or stored in a WARC file. For more information about memento and TimeMaps, see http://timetravel.mementoweb.org/about/ and https://tools.ietf.org/html/rfc7089. For more information about WARC files, see http://archive-access.sourceforge.net/warc/. For information about Archive-It, see https://archive-it.org.

# Start by Using Docker (preferred method)

To download the latest image corresponding with a stable release of this code
```
docker pull shawnmjones/offtopic-archive-analysis:latest
```

Then start the docker image in the background
```
docker run -td shawnmjones/offtopic-archive-analysis --name offtopic
```

To analyze a collection, run a command like the following. The ```-i``` and ```-o``` options are mandatory.
```
docker exec off-topic python detect_off_topic.py -i archiveit=3936 -o outputfile
```

Analysis is done one of several input types supplied by the ```-i``` option on the command line. Information about off-topic mementos are stored in a file specified by the ```-o``` option.

## Input Types

To analyze a given Archive-It collection use the ```-i``` option with the word ```archiveit``` and the collection number supplied after an ```=``` sign, like so:
```
docker exec off-topic python detect_off_topic.py -i archiveit=3936 -o outputfile
```

To analyze a TimeMap use the ```-i``` option with the word ```timemap``` and the TimeMap URI supplied after an ```=``` sign, like so:
```
docker exec off-topic python detect_off_topic.py -i timemap=http://wayback.archive-it.org/3936/timemap/link/http://www.doi.gov/index.cfm  -o outputfile
```

Multiple TimeMap URIS can be supplied separated by commas without a space.

To analyze WARC files, use the ```-i``` option with the word ```warc``` and the WARC file names supplied after an ```=``` sign, separated by commas without spaces, like so:
```
docker exec off-topic python detect_off_topic.py -i warc=warc1.warc.gz,warc2.warc.gz -o outputfile
```

Finally, if you have already downloaded data using this tool into a directory, you can supply that as well:
```
docker exec off-topic python detect_off_topic.py -i dir=/tmp/working -o outputfile
```

## Algorithms

This software contains several different measurement algorithms for analysis. So far, they are as follows:
* bytecount - A comparison of the percentage of bytes that changed between the first memento in TimeMap and the other mementos from that TimeMap.
* wordcount - Like bytecount, but with words instead of bytes.
* jaccard - The Jaccard distance between the first memento and the other mementos in each TimeMap in a collection.
* cosine - The cosine similarity of the first memento with the other mementos in each TimeMap in a collection.
* tfintersection - The difference between the top 20 terms of the first memento compared to the other mementos in each TimeMap in a collection.

By default, the system uses the cosine and wordcount algorithms with thresholds of 0.15 and -0.85, respectively.

Algorithms can be supplied on the command line using the ```-m``` option along with the name of the algorithm and an optional threshold specified after an ```=```:
```
docker exec off-topic python detect_off_topic.py -i archiveit=3936 -o outputfile -m jaccard=0.10,cosine=0.20
```

### Other Optional Arguments

One can also specify:
* ```-l``` to specify a log file (by default the application logs to stdout)
* ```-d``` to change the working directory where data is downloaded and processed (by default /tmp/working)
* ```-v``` to enable extra debugging statements in the log file

# To Set Up Development Environment for GitHub code checkout

## Prerequisite
* Python 3.6
* java 1.7+

To install the Python prerequisites:

```
pip install -r requirements.txt
python -m nltk.downloader punkt
```

To install boilerpipe library:

```
git clone https://github.com/misja/python-boilerpipe.git
cd python-boilerpipe
wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/boilerpipe/boilerpipe-1.2.0-bin.tar.gz
python setup.py install
```
  
# Feedback
Your feedback is always welcome. You can send me an email on sjone@cs.odu.edu or open an issue on github.
