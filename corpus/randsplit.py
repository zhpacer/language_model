from cmath import log
#import imp
import sys
import re
import math
import argparse
import random
#from ngram_train import *

def RandomSplit(input,ratio,output):
        f = open(input,"r",encoding='utf-8')
        o = open(output,"w",encoding='utf-8')
        line = f.readline()
        while len(line) > 0: 
            line = line.lstrip()
            line = line.rstrip()
            prob = random.random()
            if prob <= float(ratio):
              o.write("%s\n" % (line))
            line = f.readline()
        f.close()
        o.close()                                         




if __name__ == '__main__':
    RandomSplit(sys.argv[1],sys.argv[2],sys.argv[3])


                

