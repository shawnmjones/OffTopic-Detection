#!/bin/sh

filename=$1

s200=`grep '\t"200"\t' ${filename} | wc -l`
s400=`grep '\t"400"\t' ${filename} | wc -l`
s401=`grep '\t"401"\t' ${filename} | wc -l`
s403=`grep '\t"403"\t' ${filename} | wc -l`
s404=`grep '\t"404"\t' ${filename} | wc -l`
s500=`grep '\t"500"\t' ${filename} | wc -l`
s502=`grep '\t"502"\t' ${filename} | wc -l`
s503=`grep '\t"503"\t' ${filename} | wc -l`
s504=`grep '\t"504"\t' ${filename} | wc -l`
err=`grep '\t"ERROR"\t' ${filename} | wc -l`

echo "200s: ${s200}"
echo "400s: ${s400}"
echo "401s: ${s401}"
echo "403s: ${s403}"
echo "404s: ${s404}"
echo "500s: ${s500}"
echo "502s: ${s502}"
echo "503s: ${s503}"
echo "504s: ${s504}"
echo "ERRORs: ${err}"
