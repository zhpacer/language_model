import sys
import re
import getopt
import ngram_count

def usage():
    print("*py -input -output [-order]")

class Ngram:
    def __init__(self,order = 3):
        self.ngram_dict = {}


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
