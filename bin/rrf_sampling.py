#!/usr/bin/python
from datetime import datetime
import json
import os
import re
import sys

lastSpaces = 0
spaces = 0
seenTypes = [] # unique term types
seenAtns = [] # unique ATNs
seenSemanticTypes = [] # unique symantic types
defintionFound = False
synonymPrinted = False
auiCodeMappings = {}
cuiCodeMappings = {}

def checkParamsValid(argv):

    if(len(argv) != 3):
        print("Usage: rrf_sampling.py <terminology RRF file path> <terminology>")
        return False
    elif(os.path.isdir(argv[1]) == False):
        print(argv[1])
        print("terminology RRF directory path is invalid")
        print("Usage: rrfSampling.py <terminology RRF file path> <terminology>")
        return False
        
    return True

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    
    if(checkParamsValid(sys.argv) == False):
        exit(1)
    
    terminology = sys.argv[2].upper()
    
    with open(terminology.lower() + "-rrf-samples.txt", "w") as termFile:
    
        with open (sys.argv[1] + "/MRCONSO.RRF", "r", encoding='utf-8') as mrconsoFile:
            mrconsoLines = mrconsoFile.readlines()
        
            for mrconsoIndex, mrconsoLine in enumerate(mrconsoLines): # get index just in case
            
                mrconsoLine = mrconsoLine.strip() # no need for leading spaces anymore
                splitLine = mrconsoLine.split("|")
                mrconsoCui = splitLine[0]
                mrconsoAui = splitLine[7]
                mrconsoUri = splitLine[10]
                mrconsoTerminology = splitLine[11]
                mrconsoTermType = splitLine[12]
                mrconsoCode = splitLine[13]
                mrconsoTerm = splitLine[14]
                
                if(mrconsoTerminology != terminology): # only process mrconsos from the terminology 
                    continue
                    
                # print("mrconsoCode: " + mrconsoCode)
                # print("mrconsoTerminology: " + mrconsoTerminology)
                # print("mrconsoTermType: " + mrconsoTermType)
                
                if(mrconsoCui not in cuiCodeMappings): # has this CUI been seen before
                    cuiCodeMappings[mrconsoCui] = mrconsoCode
                    
                if(mrconsoAui not in auiCodeMappings): # has this AUI been seen before
                    auiCodeMappings[mrconsoAui] = mrconsoCode
                
                if(synonymPrinted == False): # print the first synonym
                    synonymPrinted = True
                    termFile.write(mrconsoUri + "\t" + mrconsoCode + "\t" + "synonym"  + "\t" + mrconsoTerm + "\n")
                    
                if(mrconsoTermType not in seenTypes): # print this term type if never seen
                    seenTypes.append(mrconsoTermType)
                    termFile.write(mrconsoUri + "\t" + mrconsoCode + "\t" + "term-type" + "\t" + mrconsoTermType + "\n")
            
        with open (sys.argv[1] + "/MRSAT.RRF", "r", encoding='utf-8') as mrsatFile:
            mrsatLines = mrsatFile.readlines()
        
            for mrsatIndex, mrsatLine in enumerate(mrsatLines): # get index just in case
                   
                mrsatLine = mrsatLine.strip() # no need for leading spaces anymore
                splitLine = mrsatLine.split("|")
                lineAui = splitLine[3]
                lineSType = splitLine[4]
                lineAtn = splitLine[8]
                lineAtv = splitLine[10]
                
                if(lineSType == 'RUI' or lineAui == 'SUBSET_MEMBER'): # do not process these 
                    continue
                
                if(lineAui not in auiCodeMappings): # must be from the terminology being processed 
                    continue
                
                code = auiCodeMappings[lineAui]
                    
                if(lineAtn not in seenAtns): # print this ATN if never seen
                    seenAtns.append(lineAtn)
                    termFile.write(code + "\t" + code + "\t" + lineAtn + "\t" + lineAtv + "\n")
                    
        with open (sys.argv[1] + "/MRSTY.RRF", "r", encoding='utf-8') as mrstyFile:
            mrstyLines = mrstyFile.readlines()
        
            for mrstyIndex, mrstyLine in enumerate(mrstyLines): # get index just in case
                   
                mrstyLine = mrstyLine.strip() # no need for leading spaces anymore
                splitLine = mrstyLine.split("|")
                lineCui = splitLine[0]
                lineSemanticType = splitLine[3]
                
                if(lineCui not in cuiCodeMappings): # must be from the terminology being processed 
                    continue
                
                code = cuiCodeMappings[lineCui]
                    
                if(lineSemanticType not in seenSemanticTypes): # print this Semantic Type if never seen
                    seenSemanticTypes.append(lineSemanticType)
                    termFile.write(code + "\t" + code + "\t" + "Semantic_Type" + "\t" + lineSemanticType + "\n")
                    
        with open (sys.argv[1] + "/MRDEF.RRF", "r", encoding='utf-8') as mrdefFile:
            mrdefLines = mrdefFile.readlines()
        
            for mrdefIndex, mrdefLine in enumerate(mrdefLines): # get index just in case
                   
                mrdefLine = mrdefLine.strip() # no need for leading spaces anymore
                splitLine = mrdefLine.split("|")
                lineAui = splitLine[1]
                lineDef = splitLine[5]
                
                if(lineAui not in auiCodeMappings): # must be from the terminology being processed 
                    continue
                
                
                code = auiCodeMappings[lineAui]
                    
                if(not defintionFound): # print this defintion if we haven't printed one
                    defintionFound = True
                    termFile.write(code + "\t" + code + "\t" + "DEFINITION" + "\t" + lineDef + "\n")
            
    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    