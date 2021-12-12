# -*- coding: UTF-8 -*-
import sys
import re
import getopt

def usage():
    print("*py -input -output [-order]")

class NgramCount:
    def __init__(self,order = 3):
        self.ngram_dict = {}
        self.input_file = ""
        self.ngram_order = int(order)
        self.sent_begin = "<s>"
        self.sent_end = "</s>"
        for order in range(self.ngram_order):
            self.ngram_dict[order+1] = {}
        
    def Count(self,file):
        f = open(file,"r",encoding='utf-8')
        line = f.readline()
        while len(line) > 0:
            line = line.lstrip()
            line = line.rstrip()
            words = line.split()
            words.insert(0,self.sent_begin)
            words.append(self.sent_end)
            for order in range(self.ngram_order):
                order = order + 1
                begin = 0
                if begin + order <= len(words):
                    word = words[begin:begin+order]
                    word_str = " ".join(word)
                    if word_str not in self.ngram_dict[order]:
                        self.ngram_dict[order][word_str] = 0
                    self.ngram_dict[order][word_str] += 1 
                index = begin + order + 1
                while index <=len(words):
                    word = words[index-order:index]
                    word_str = " ".join(word)
                    if word_str not in self.ngram_dict[order]:
                        self.ngram_dict[order][word_str] = 0                    
                    self.ngram_dict[order][word_str] += 1 
                    index = index + 1
            line = f.readline()
        f.close()


    def GetNgramCount(self):
        return self.ngram_dict
    def WriteCount(self,ouput):
        o = open(ouput,"w",encoding='utf-8')
        for order in range(self.ngram_order): 
            order = order + 1
            for (word,count) in self.ngram_dict[order].items():
                o.write("%s\t%d\n" % (word,count) )
        o.close()


