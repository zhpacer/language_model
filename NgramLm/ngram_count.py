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
        f = open(file,"r")
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


    def WriteCount(self,ouput):
        o = open(ouput,"w")
        for order in range(self.ngram_order): 
            order = order + 1
            for (word,count) in self.ngram_dict[order].items():
                o.write("%s\t%d\n" % (word,count) )
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
