#!/bin/sh

filename=$1

tp=`grep True.*True ${filename} | wc -l`
tn=`grep False.*False ${filename} | wc -l`
fp=`grep False.*True ${filename} | wc -l`
fn=`grep True.*False ${filename} | wc -l`

echo "TP: ${tp}"
echo "TN: ${tn}"
echo "FP: ${fp}"
echo "FN: ${fn}"
