#!/bin/bash

count=`ls -1 *.hc22000 2>/dev/null | wc -l`
if [ $count != 0 ]
then 
echo $count "hash file(s) found." 
else
echo "No hash files."
fi
