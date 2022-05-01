from audioop import add
from select import select
import sys
import re
import math
import argparse
from pyspark import SparkContext, SparkConf

#sample usage: spark-submit  ngram_lm_train.py -order 3 -input ../corpus/en_sample.txt -lm ./en_sample.3lm


def getParser():
    parser = argparse.ArgumentParser(description='process parameters for ngram')
    parser.add_argument('-input',type=str,nargs='?',help='the input text for ngram')
    parser.add_argument('-count',type=str,nargs='?',help='the output count file')
    parser.add_argument('-order',type=int,nargs='?',help='the ngram order ')
    parser.add_argument('-discount',type=str,nargs='?',default='cdiscount',help='discount method')
    parser.add_argument('-discount_params',type=str,nargs='?',default='0.5',help='parameters for the discount method')
    parser.add_argument('-gt3min',type=int,nargs='?',default='2',help='the count value to limit the 3gram with count small than it')
    parser.add_argument('-gt4min',type=int,nargs='?',default='2',help='the count value to limit the 4gram with count small than it')
    parser.add_argument('-gt5min',type=int,nargs='?',default='2',help='the count value to limit the 5gram with count small than it')
    parser.add_argument('-lm',type=str,nargs='?',default='ngram.lm',help='the lm output file')
    return parser

def checkArgs(parser,args):
    if ((args is None) or (args.input is None) or (len(args.input) <= 0) or (args.lm is None) or (len(args.lm) <= 0)):
        parser.print_help()
        sys.exit(0)

class NgramSplit(object):
    def __init__(self,order=3):
        self.ngramOrder = int(order)
        self.sentBegin = "<s>"
        self.sentEnd = "</s>"
    def countLine(self, line):
        ngramDict = {}
        #for order in range(self.ngram_order):
        #    ngram_dict[order+1] = {}
        line = line.lstrip()
        line = line.rstrip()
        words = line.split()
        words.insert(0,self.sentBegin)
        words.append(self.sentEnd)
        for order in range(self.ngramOrder):
            order = order + 1
            begin = 0
            if begin + order <= len(words):
                word = words[begin:begin+order]
                wordStr = " ".join(word)
                if wordStr not in ngramDict:
                    ngramDict[wordStr] = 0
                ngramDict[wordStr] += 1 
                index = begin + order + 1
            while index <=len(words):
                word = words[index-order:index]
                wordStr = " ".join(word)
                if wordStr not in ngramDict:
                    ngramDict[wordStr] = 0                    
                ngramDict[wordStr] += 1 
                index = index + 1        
        return [(k,v) for k,v in ngramDict.items()]
    def count(self, rdd):
        return rdd.flatMap(self.countLine)
class NgramTrain(object):
    def __init__(self,unigramCount,totalUnigramCount,gt3min=2,gt4min=2,gt5min=2,order = 3,dsicountMethod = "cd"):
        self.order = order
        self.discountMethod = dsicountMethod
        self.cdiscountValue = 0.5
        self.totalUnigramCount = totalUnigramCount
        self.unigramCount = unigramCount
        self.unigramProb = {}
        self.calcUnigramRawProb()
        self.gt3min = gt3min
        self.gt4min = gt4min
        self.gt5min = gt5min
        self.defaultBackoffProb = -99
        self.sentBegin = "<s>"
        self.sentEnd = "</s>"

    def calcUnigramRawProb(self):
        for (k,v) in self.unigramCount.items():
            prob = math.log10(float(v)/float(self.totalUnigramCount))
            self.unigramProb[k] = prob

    def filterCount(self,value):
        ngram = value[0]
        count = value[1]
        order = len(ngram.split())
        if order == 3 and count < self.gt3min:
            return False
        if order == 4 and count < self.gt4min:
            return False        
        if order == 5 and count < self.gt5min:
            return False
        return True
    def filterUnigram(self,ngram):
        return len(ngram[0].split()) == 1
    def mapNgramForProb(self,ngram):
        # for each ngram of w1w2..wn, create two pairs:
        # (w1w2..wn,(w1w2..wn,count)),(w1w2..wn-1,(w1w2..wn,count))
        wds = ngram[0].split()
        ngramOrdr = len(wds)
        mapDict = {}
        mapDict[ngram[0]] = ngram
        if ngramOrdr > 1:
            prefix = " ".join(wds[0:ngramOrdr-1])
            mapDict[prefix] = ngram
        return [(k,v) for k,v in mapDict.items()]
    def mapNgramForBackoff(self,value):
        # for each ngram of w1w2..wn, create at least three pairs:
        # (w1w2..wn,(w1w2..wn,count)),(w1w2..wn-1,(w1w2..wn,count)),(w2..wn,(w1w2..wn,count))
        # if the ngram's order is greater than 2, will create a new pair:
        # (w2..wn-1,(w1w2..wn,count))
        wds = value[0].split()
        ngramOrdr = len(wds)
        mapDict = {}
        mapDict[value[0]] = value
        if ngramOrdr > 1:
            prefix = " ".join(wds[0:ngramOrdr-1])
            suffix = " ".join(wds[1:ngramOrdr])
            mapDict[prefix] = value
            mapDict[suffix] = value
        if ngramOrdr > 2:
            key = " ".join(wds[1:ngramOrdr-1])
            mapDict[key] = value
        return [(k,v) for k,v in mapDict.items()]

    def calcNgramProb(self,value):
        baseCount = 0
        mapDict ={}
        if len(value) > 1:
            ngram = value[0]
            mapValues = value[1]
            for (k,v) in mapValues:
                if k == ngram:
                    baseCount = v
                    break
            for (k,v) in mapValues:
                if len(k.split()) > 1:
                    v = float(v) - float(self.cdiscountValue)
                if k != ngram:
                    rawProb = math.log10(float(v)/float(baseCount))
                    mapDict[k] = rawProb
                else:
                    if len(k.split()) == 1:
                        rawProb = math.log10(float(v)/float(self.totalUnigramCount))
                        if k == self.sentBegin:
                            rawProb = -99
                        mapDict[k] = rawProb
            #baseCount  = baseCount + ngram
        else:
            print("error pair for %d "  % (value[0]))
        #    baseCount  = baseCount + c
        return [(k,v) for k,v in mapDict.items()]
    
    def calcBackoff(self,kvPair):
        mapDict ={}
        if len(kvPair) > 1:
            ngram = kvPair[0]
            map_values = kvPair[1]
            order = len(ngram.split())
            #suppose ngram=w1..wn,contain all the pairs of: (w1..wn,(w1..wn*,prob))
            prefixMap = {}
            #suppose ngram=w1..wn,contain all the pairs of: (w1..wn,(*w1..wn,prob))
            suffixMap = {}
            #suppose ngram=w1..wn,contain all the pairs of: (w1..wn,(*w1..wn*,prob))
            middleMap = {}
            exact_match_ngram = ""
            exactMatchNgramProb = 0.0
            if order >= self.order:
                for (k,v) in map_values:
                    return [(k,(v,0.0))]
            for (k,v) in map_values:
                wds = k.split()
                if " ".join(wds[0:len(wds)-1]) == ngram and (len(wds) == (order +1)):
                    prefixMap[k] = v
                if " ".join(wds[1:len(wds)]) == ngram and (len(wds) == (order +1)):
                    suffixMap[k] = v
                if " ".join(wds[1:len(wds)-1]) == ngram:
                    middleMap[k] = v
                if k == ngram:
                    exact_match_ngram = k
                    exactMatchNgramProb = v                
            #print("prefix size %d, suffix size %d, middle size %d for %s\n" % (len(prefixMap.keys()),len(suffixMap.keys()),len(middleMap.keys()),ngram))
            if order == 1:
                totalBigramProb = 0.0
                unigramList = []
                ngram_prob = 0.0
                for (k,v) in prefixMap.items():
                    wds = k.split()
                    prob = v
                    if wds[0] == ngram and len(wds) == 2:
                        totalBigramProb = totalBigramProb + 10 ** prob
                        unigramList.append(wds[1])
                totalUnigramProb = 0.0
                for w in unigramList:
                    #get the unigram prob from pre-caculated map
                    totalUnigramProb = totalUnigramProb + 10 ** self.unigramProb[w]
                backoffProb = self.defaultBackoffProb
                if (1-totalUnigramProb) > 0:
                    backoffProb = math.log10(float(1-totalBigramProb)/float(1-totalUnigramProb))
                if backoffProb >= 0:
                    backoffProb = self.defaultBackoffProb
                mapDict[ngram] = (exactMatchNgramProb,backoffProb)
            for (k,v) in suffixMap.items():
                    currentNgram = k
                    currentNgramProb = v
                    totalNProb = 0.0
                    totalNMinus1Prob = 0.0
                    occurNgramList = {}
                    for (mk,mv) in middleMap.items():
                        wds = mk.split()
                        #find the suffix ngram in the middle to get the probility
                        if " ".join(wds[0:len(wds)-1]) == currentNgram:
                            totalNProb = totalNProb + 10 ** mv
                            occurNgramList[" ".join(wds[1:len(wds)])] = 1
                    for (ok,ov) in occurNgramList.items():
                        if ok in prefixMap:
                            totalNMinus1Prob += 10 ** prefixMap[ok]
                        else:
                            print("error can't find suffix %s" % (k))
                    currentNgramBackoff = self.defaultBackoffProb
                    if (1-totalNMinus1Prob) > 0:
                        currentNgramBackoff = math.log10(float(1-totalNProb)/float(1-totalNMinus1Prob))
                    if currentNgramBackoff >= 0:
                        currentNgramBackoff = self.defaultBackoffProb
                    #if len(occur_ngram_list.keys()) > 0:
                        #print("find ngram size %d for %s" % (len(occur_ngram_list.keys()),current_ngram))
                    mapDict[currentNgram] = (currentNgramProb,currentNgramBackoff)
        else:
            print("error pair for %d "  % (kvPair[0]))
        #    baseCount  = baseCount + c
        return [(k,v) for k,v in mapDict.items()]
    def convertToArpa(self,lmRdd,writeFile):
        ngramLM = {}
        for i in range(self.order):
            currentOrdr = i + 1
            ngramLM[currentOrdr] = {}
        count = lmRdd.count()
        for item in lmRdd.collect():
            ngram = item[0]
            prob = item[1][0]
            backoff = item[1][1]
            order = len(ngram.split())
            if ngram not in ngramLM[order]:
                ngramLM[order][ngram] = {}
            ngramLM[order][ngram]["prob"]=prob
            ngramLM[order][ngram]["backoff"]=backoff
        self.writeArapa(ngramLM,self.order,writeFile)

    def writeArapa(self,lmProb,ngramOrder,writeFile):
       o = open(writeFile,"w",encoding='utf-8')
       o.write("\n\data\\\n\n")
       for order in range(ngramOrder): 
            order = order + 1
            o.write("ngram %d=%d\n" % (order,len(lmProb[order].keys())))
       o.write("\n")
       for order in range(ngramOrder): 
            order = order + 1
            o.write("\%d-grams:\n" % (order))
            for word in sorted(lmProb[order].keys()):
                backoff = lmProb[order][word]["backoff"]
                if backoff <= 0 and backoff != self.defaultBackoffProb: 
                    o.write("%f\t%s\t%f\n" % (lmProb[order][word]["prob"],word,lmProb[order][word]["backoff"]) )
                elif backoff > 0:
                    o.write("%f\t%s\t0\n" % (lmProb[order][word]["prob"],word) )
                else:
                    o.write("%f\t%s\n" % (lmProb[order][word]["prob"],word) )

            o.write("\n")
       o.write("\end\\\n")
       o.close()        
            
def ngramLmTrain(sc,args):
    ngram = NgramSplit(args.order)
    lines = sc.textFile(args.input)
    sepLines=ngram.count(lines)
    #get the count
    counts=sepLines.reduceByKey(lambda a, b: a + b)
    #caculate the unigram count
    unigramCount = counts.filter(lambda a: len(a[0].split()) == 1 and a[0] != ngram.sentBegin).map(lambda a:a[1]).reduce(lambda a,b: a+b)
    #get the unigram list
    unigramList = counts.filter(lambda a: len(a[0].split()) == 1).collectAsMap()
    #create the ngram lm trainer
    trainer = NgramTrain(unigramList,unigramCount,args.gt3min,args.gt4min,args.gt5min,args.order)
    print("unigram count %d " % (unigramCount))
    #step1 map all the ngrams to calculate the proablility
    mapCounts = counts.filter(trainer.filterCount).flatMap(trainer.mapNgramForProb)
    if (args.count is not None) and len(args.count) > 0:
        countWriter = open(args.count,"w",encoding='utf-8')
        for ngramCount in counts.collect():
            countWriter.write("%s\t%d\n" % (ngramCount[0],ngramCount[1]))
        countWriter.close()
    #step2 group ngrams by the keys
    mapCountsGroup = mapCounts.groupByKey()
    #step3 calculate the probability for each ngram
    probCounts = mapCountsGroup.flatMap(trainer.calcNgramProb)
    #step4 map all the ngrams to calculate the backoff
    backoffCounts = probCounts.flatMap(trainer.mapNgramForBackoff)
    #step5 caculate the back off for each ngram
    lmProb=backoffCounts.groupByKey().flatMap(trainer.calcBackoff)
    #step6 write the lm to the arpa format
    trainer.convertToArpa(lmProb, args.lm)
        

    


if __name__ == '__main__':
    parser = getParser()
    args = parser.parse_args()
    checkArgs(parser,args)
    for arg in vars(args):
        print("%s : %s" % (arg,getattr(args,arg)))
    conf = SparkConf().setAppName("zh-test").setMaster("local")
    sc = SparkContext(conf=conf)
    #lines = sc.textFile("../corpus/en_sample.txt")
    ngramLmTrain(sc,args)
     





#usage spark-submit *.py