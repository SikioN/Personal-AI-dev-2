#!/bin/bash

# 3483 dialogues
# each batch will have info about 40 dialogues
# = > 3483 / 40 = 88 batches

# error with 1 part

for i in {0..87}
do
   echo "start calculation $i batch"
   python3 memorize_extract.py --batch=$i
done
