from cmath import log
#import imp
import sys
import re
import math
import argparse
from ngram_count import *
#from ngram_train import *

def get_parser():
    parser = argparse.ArgumentParser(description='process parameters for ngram')
    parser.add_argument('-lm',type=str,nargs='?',help='the trained language model')
    parser.add_argument('-order',type=int,nargs='?',help='the ngram order ')
    parser.add_argument('-text',type=str,nargs='?',help='the input text to be processed ')
    parser.add_argument('-output',type=str,nargs='?',help='the output file')
    return parser

def check_args(parser,args):
    if ((args is None)  or (args.lm is None) or (args.order is None) or (args.output is None) or (args.text is None)) :
        parser.print_help()
        sys.exit(0)


class Ngram:
    def __init__(self,args):
        self.lm = args.lm
        self.order = args.order
        self.ngram_prob = {}
        self.sent_begin = "<s>"
        self.sent_end = "</s>"
        
        if self.order < 1:
            print("order is not right(should bigger than 1)")
            sys.exit(0)
        for i in range(self.order):
            i = i+1
            if i not in self.ngram_prob:
                self.ngram_prob[i] = {}
        self.ReadLM(self.lm)
    
    def ReadLM(self,lm_name):
        f = open(lm_name,"r",encoding='utf-8')
        line = f.readline()
        while len(line) > 0:
            line = line.lstrip()
            line = line.rstrip()
            parts = line.split('\t')
            if len(parts) > 1:
                prob = float(parts[0])
                wds = parts[1].split()
                order = len(wds)
                backoff = 0.0
                if len(parts) > 2:
                    backoff = float(parts[2])
                if parts[1] not in self.ngram_prob[order]:
                    self.ngram_prob[order][parts[1]]= []
                    self.ngram_prob[order][parts[1]].append(prob)
                    self.ngram_prob[order][parts[1]].append(backoff)
            line = f.readline()
        f.close()
    
    
    def CalcNgramProb(self,ngram,order):
        if ngram in self.ngram_prob[order]:
            return self.ngram_prob[order][ngram][0]
        else:
            #now backoff
            if order == 1:
                return 0.0
            wds = ngram.split()
            backoff_ngram = " ".join(wds[0:order-1])
            remain_ngram = " ".join(wds[1:order])
            backoff_prob = 0.0
            if backoff_ngram in self.ngram_prob[order-1]:
                backoff_prob = backoff_prob + self.ngram_prob[order-1][backoff_ngram][1]
            return backoff_prob + self.CalcNgramProb(remain_ngram,order-1)

    def CalcLineProb(self,line):
        length = len(line)
        index = 1
        logprob = 0.0
        while index < self.order and index < length:
            ngram = " ".join(line[0:index+1])
            order = index + 1
            logprob = logprob + self.CalcNgramProb(ngram,order)
            index = index + 1
        while index < length:
            begin = index - self.order + 1
            ngram = " ".join(line[begin:index+1])
            logprob = logprob + self.CalcNgramProb(ngram,self.order)
            index = index + 1
        return logprob


    def CalcProb(self,input,output):
        f = open(input,"r",encoding='utf-8')
        o = open(output,"w",encoding='utf-8')
        line = f.readline()
        total_logprob = 0.0
        total_word_num = 0.0
        total_sent_num = 0.0
        while len(line) > 0: 
            line = line.lstrip()
            line = line.rstrip()
            wds = line.split()
            word_num = len(wds)
            wds.insert(0,self.sent_begin)
            wds.append(self.sent_end)
            logprob = self.CalcLineProb(wds)
            length = len(wds)
            prob = 10**logprob
            factor = -float(1)/float(word_num)
            ppl1= prob ** factor
            ppl= prob ** (-float(1)/float(word_num+1))
            total_sent_num  = total_sent_num + 1
            total_word_num = total_word_num + word_num
            total_logprob = total_logprob + logprob
            #log_ppl = logprob*factor
            o.write("%s\tlogprob=%f\tppl=%f\tppl1=%f\n" % (line,logprob,ppl,ppl1))
            line = f.readline()
        ppl= (10**total_logprob) ** (-float(1)/float(total_word_num+total_sent_num))
        ppl1 = (10**total_logprob) ** (-float(1)/float(total_word_num))
        o.write("the whole file %s logprob=%f\tppl=%f\tppl1=%f\n" % (input,total_logprob,ppl,ppl1))
        f.close()
        o.close()       
                                    




if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    check_args(parser,args)
    for arg in vars(args):
        print("%s : %s" % (arg,getattr(args,arg)))
    
    ngram = Ngram(args)
    ngram.CalcProb(args.text,args.output)


                

