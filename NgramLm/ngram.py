import sys
import re
import math
import argparse
from ngram_count import *

def get_parser():
    parser = argparse.ArgumentParser(description='process parameters for ngram')
    parser.add_argument('-input',type=str,nargs='?',help='the input text for ngram')
    parser.add_argument('-count',type=str,nargs='?',help='the output count file')
    parser.add_argument('-order',type=int,nargs='?',help='the ngram order ')
    parser.add_argument('-discount',type=str,nargs='?',default='cdiscount',help='discount method')
    parser.add_argument('-discount_params',type=str,nargs='?',default='0.5',help='parameters for the discount method')
    parser.add_argument('-gt3min',type=int,nargs='?',default='2',help='the count value to limit the 3gram with count small than it')
    parser.add_argument('-gt4min',type=int,nargs='?',default='2',help='the count value to limit the 4gram with count small than it')
    parser.add_argument('-gt5min',type=int,nargs='?',default='2',help='the count value to limit the 5gram with count small than it')

    
    parser.add_argument('-lm',type=str,nargs='?',default='ngram.lm',help='the lm output fle')
    return parser
def check_args(parser,args):
    if ((args is None) or (args.input is None) or (len(args.input) <= 0) or (args.count is None) or (len(args.count) <= 0)):
        parser.print_help()
        sys.exit(0)



def usage():
    print("*py -input -output [-order]")

class Ngram:
    def __init__(self,ngram_count,args):
        self.ngram_count = ngram_count
        self.ngram_prob = {}
        self.ngram_prefix_count = {}
        self.ngram_order = int(args.order)
        self.discount_method = args.discount
        self.discount_args = {}
        self.ngram_prefix = {}
        self.ngram_suffix = {}
        self.sent_begin = "<s>"
        self.sent_end = "</s>"
        self.gt3min =args.gt3min
        self.gt4min =args.gt4min
        self.gt5min =args.gt5min

        if self.discount_method == 'cdiscount':
            absolute_discount = float(args.discount_params)
            self.discount_args["absolute_discount"] = absolute_discount
        for order in range(self.ngram_order):
            self.ngram_prob[order+1] = {}
            self.ngram_prefix[order+1] = {}
            self.ngram_suffix[order+1] = {}
            self.ngram_prefix_count[order+1] ={}
    
    def CalcPrefixNgramRemainProb(self,ngram,order):
        #ngram: WiWi-1Wi-2..Wi-n+1
        # calculate 1- sum(P(W*|WiWi-1Wi-2..Wi-n+1)) (for Count(W*WiWi-1Wi-2..Wi-n+1) >0)
        sum_prob = 0.0
        order = order + 1
        if ngram not in self.ngram_prefix[order-1]:
            return sum_prob
        for cur_ngram in self.ngram_prefix[order-1][ngram].keys():
            sum_prob += 10 ** (self.ngram_prob[order][cur_ngram]["prob"])
        return 1-sum_prob
    def CalcSuffixNgramRemainProb(self,ngram,order):
        #ngram: WiWi-1Wi-2..Wi-n+1
        ## calculate 1- sum(P(Wi|Wi-1Wi-2..Wi-n+2) (for Count(W*|WiWi-1Wi-2..Wi-n+1) >0)
        sum_prob = 0.0
        ngram_wds = ngram.split()
        #suffix_ngram = " ".join(ngram_wds[1:len(ngram_wds)])
        if ngram not in self.ngram_suffix[order]:
            return sum_prob
        for cur_ngram in self.ngram_suffix[order][ngram].keys():
            sum_prob += 10 ** (self.ngram_prob[order][cur_ngram]["prob"])
        #for cur_ngram in self.ngram_prob[order].keys():
        #    wds = cur_ngram.split()
        #    prefix_ngram = " ".join(wds[0:len(wds)-1])
        #    if prefix_ngram  == ngram:
        #        ngram_wds = cur_ngram.split()
        #        suffix_ngram = " ".join(ngram_wds[1:len(ngram_wds)])
        #        sum_prob += self.ngram_prob[order-1][suffix_ngram]["prob"]
        return 1-sum_prob

    def CalcBackoffProb(self):
        for order in range(self.ngram_order):
            order = order + 1
            if order >= self.ngram_order:
                break
            for ngram in self.ngram_prob[order].keys():
                remain_prob = self.CalcPrefixNgramRemainProb(ngram,order)
                base_prob = self.CalcSuffixNgramRemainProb(ngram,order)
                backoff_prob = 0.0
                if base_prob == 0:
                    backoff_prob = 0.0
                else:
                    backoff_prob = math.log10(remain_prob/base_prob)
                    if backoff_prob > 0:
                        backoff_prob = 0
                self.ngram_prob[order][ngram]["backoff"] = backoff_prob
    def CalcProb(self):
        self.CalcDiscountProb()
        print("Now calculate backoff prob")
        self.CalcBackoffProb()    
    def CalcDiscountProb(self):
        total_unigram_count = 0
        reduce_count = self.discount_args["absolute_discount"]
        if len(self.ngram_count.keys()) < self.ngram_order:
            return
        for (ngram,count) in self.ngram_count[1].items():
            #and ngram != self.sent_end
            if ngram != self.sent_begin:
                total_unigram_count = total_unigram_count + count
        
        for order in range(self.ngram_order):
            order = order + 1
            for (ngram,count) in self.ngram_count[order].items():
                if order == 1:
                    #-float(reduce_count)
                    raw_prob = (float(count))/float(total_unigram_count)
                    if ngram not in self.ngram_prob[order]:
                        self.ngram_prob[order][ngram] = {}
                    if ngram == self.sent_begin:
                        self.ngram_prob[order][ngram]["prob"]= -99
                    else:
                        self.ngram_prob[order][ngram]["prob"]=math.log10(raw_prob)
                    self.ngram_prob[order][ngram]["backoff"]=0.0
                else:
                    if order == 3 and count < self.gt3min:
                        continue
                    if order == 4 and count < self.gt3min:
                        continue                    
                    if order == 5 and count < self.gt3min:
                        continue
                    words = ngram.split()
                    prefix = " ".join(words[0:len(words)-1])
                    suffix = " ".join(words[1:len(words)])
                    if prefix not in self.ngram_prefix[order-1]:
                        self.ngram_prefix[order-1][prefix] = {}
                    if prefix not in self.ngram_suffix[order-1]:
                        self.ngram_suffix[order-1][prefix] = {}
                    self.ngram_prefix[order-1][prefix][ngram] = 1
                    self.ngram_suffix[order-1][prefix][suffix] = 1
                    base_count = self.ngram_count[order-1][prefix]
                    raw_prob = float(count-reduce_count)/float(base_count)
                    if ngram not in self.ngram_prob[order]:
                        self.ngram_prob[order][ngram] = {}
                    self.ngram_prob[order][ngram]["prob"]=math.log10(raw_prob)
                    self.ngram_prob[order][ngram]["backoff"]=0.0
    def WriteProb(self,prob_file):
        o = open(prob_file,"w",encoding='utf-8')
        for order in range(self.ngram_order): 
            order = order + 1
            o.write("order %d = %d\n" % (order,len(self.ngram_prob[order].keys())))
            for word in self.ngram_prob[order].keys():
                o.write("%s\t%f\t%f\n" % (word,self.ngram_prob[order][word]["prob"],self.ngram_prob[order][word]["backoff"]) )
        o.close()
    def WriteArapa(self,prob_file):
       o = open(prob_file,"w",encoding='utf-8')
       o.write("\data\n\n")
       for order in range(self.ngram_order): 
            order = order + 1
            o.write("order %d = %d\n" % (order,len(self.ngram_prob[order].keys())))
       o.write("\n\n")
       for order in range(self.ngram_order): 
            order = order + 1
            o.write("\%d-grams:\n" % (order))
            for word in sorted(self.ngram_prob[order].keys()):
                backoff = self.ngram_prob[order][word]["backoff"]
                if backoff < 0: 
                    o.write("%f\t%s\t%f\n" % (self.ngram_prob[order][word]["prob"],word,self.ngram_prob[order][word]["backoff"]) )
                else:
                    o.write("%f\t%s\n" % (self.ngram_prob[order][word]["prob"],word) )

            o.write("\n\n")
       o.write("\end\\\n")

                                    



                





if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    check_args(parser,args)
    for arg in vars(args):
        print("%s : %s" % (arg,getattr(args,arg)))

    
    ngram_count = NgramCount(args.order)
    ngram_count.Count(args.input)
    ngram_count.WriteCount(args.count)
    print("finish ngram count")
    ngram_prob = Ngram(ngram_count.GetNgramCount(),args)
    ngram_prob.CalcProb()
    #ngram_prob.WriteProb(args.lm)
    ngram_prob.WriteArapa(args.lm)
    print("finish lm training")
