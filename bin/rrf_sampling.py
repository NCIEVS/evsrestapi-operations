#!/usr/bin/python
from datetime import datetime
import json
import os
import re
import sys

lastSpaces = 0
spaces = 0
seenTypes = [] # unique term types
synonymPrinted = False

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
    with open (sys.argv[1] + "/MRCONSO.RRF", "r", encoding='utf-8') as rrfFile:
        rrfLines = rrfFile.readlines()
    terminology = sys.argv[2].upper()
    
    with open("samples/" + terminology.lower() + "-rrf-samples.txt", "w") as termFile:
        for index, line in enumerate(rrfLines): # get index just in case
            lastSpaces = spaces # previous line's number of leading spaces (for comparison)
            spaces = len(line) - len(line.lstrip()) # current number of spaces (for stack level checking)
            line = line.strip() # no need for leading spaces anymore
            splitLine = line.split("|")
            lineUri = splitLine[10]
            lineTerminology = splitLine[11]
            lineTermType = splitLine[12]
            lineCode = splitLine[13]
            lineTerm = splitLine[14]
            
            if(lineTerminology != terminology): # only process lines from the terminology 
                continue
                
            # print("lineCode: " + lineCode)
            # print("lineTerminology: " + lineTerminology)
            # print("lineTermType: " + lineTermType)
            
            if(synonymPrinted == False): # print the first synonym
            	synonymPrinted = True
            	termFile.write(lineUri + "\t" + lineCode + "\t" + "synonym"  + "\t" + lineTerm + "\n")
            	
            if(lineTermType not in seenTypes): # print this term type if never seen
                seenTypes.append(lineTermType)
                termFile.write(lineUri + "\t" + lineCode + "\t" + "term-type"  + "\t" + lineTermType + "\n")
            
    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    