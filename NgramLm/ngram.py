import sys
import re
import getopt
from ngram_count import *

def usage():
    print("*py -input -output [-order]")

class Ngram:
    def __init__(self,ngram_count,order = 3,discount = 'absolute discount'):
        self.ngram_count = ngram_count
        self.ngram_prob = {}
        self.ngram_prefix_count = {}
        self.ngram_order = int(order)
        self.discount_method = discount
        for order in range(self.ngram_order):
            self.ngram_prob[order+1] = {}
            self.ngram_prefix_count[order+1] ={}
    
    def CalcProb(self):
        total_unigram_count = 0
        if len(self.ngram_count.keys()) < self.ngram_order:
            return
        for (ngram,count) in self.ngram_count[1].items():
            total_unigram_count = total_unigram_count + count
        
        for order in range(self.ngram_order):
            order = order + 1
            for (ngram,count) in self.ngram_count[order].items():
                if order == 1:
                    raw_prob = float(count)/float(total_unigram_count)
                    if ngram not in self.ngram_prob[order]:
                        self.ngram_prob[order][ngram] = {}
                    self.ngram_prob[order][ngram]["prob"]=raw_prob
                    self.ngram_prob[order][ngram]["backoff"]=0.0
                else:
                    words = ngram.split()
                    prefix = " ".join(words[0:len(words)-1])
                    base_count = self.ngram_count[order-1][prefix]
                    raw_prob = count/base_count
                    if ngram not in self.ngram_prob[order]:
                        self.ngram_prob[order][ngram] = {}
                    self.ngram_prob[order][ngram]["prob"]=raw_prob
                    self.ngram_prob[order][ngram]["backoff"]=0.0
    def WriteProb(self,prob_file):
        o = open(prob_file,"w",encoding='utf-8')
        for order in range(self.ngram_order): 
            order = order + 1
            o.write("order %d = %d\n" % (order,len(self.ngram_prob[order].keys())))
            for word in self.ngram_prob[order].keys():
                o.write("%s\t%f\t%f\n" % (word,self.ngram_prob[order][word]["prob"],self.ngram_prob[order][word]["backoff"]) )
        o.close()
                                    



                





if __name__ == '__main__':
    opts,args = getopt.getopt(sys.argv[1:],"hi:o:r:",["help","input","output","order"])
    arg_dict = {}
    default_order = 5
    for op,value in opts:
        if op in ("-i","-input"):
            arg_dict["input"] = value
        elif op in ("-o","-output"):
            arg_dict["output"] = value
        elif op in ("-order","-r"):
            arg_dict["order"] = int(value)
            default_order = value            
        elif op in ("-h","-help"):
           usage()
           sys.exit()
    if ("input" not in arg_dict.keys()) or ("output" not in arg_dict.keys()):
        usage()
        sys.exit()
    else:
        print("input:%s, output:%s, order:%d" % (arg_dict["input"],arg_dict["output"],arg_dict["order"]))
    ngram_count = NgramCount(default_order)
    ngram_count.Count(arg_dict["input"])
    ngram_count.WriteCount(arg_dict["output"])
    ngram_prob = Ngram(ngram_count.GetNgramCount(),default_order)
    ngram_prob.CalcProb()
    ngram_prob.WriteProb("test.prob")
