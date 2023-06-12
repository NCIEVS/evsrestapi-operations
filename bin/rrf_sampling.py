#!/usr/bin/python
from datetime import datetime
import json
import os
import re
import sys

lastSpaces = 0
spaces = 0
seenTypes = []
seenAtns = []
seenRuiAtns = []
seenRelas = []
seenRels = []
seenSynonymTypeAtns = []
seenSemanticTypes = []
defintionFound = False
synonymPrinted = False
auiCodeMappings = {}
cuiCodeMappings = {}
mrsatRuiAtnInfo = {}
configData = {}
listAui1 = []
listAui2 = []
auiNumberParents = {}
parentCountsSeen = []

def checkParamsValid(argv):

    if(len(argv) != 4):
    
        print("Usage: rrf_sampling.py <terminology RRF file path> <terminology config file path> <terminology>")
        return False
        
    elif(os.path.isdir(argv[1]) == False):
    
        print(argv[1])
        print("terminology RRF directory path is invalid")
        print("Usage: rrfSampling.py <terminology RRF file path> <terminology config file path> <terminology>")
        return False
        
    elif(os.path.isdir(argv[2]) == False):
    
        print(argv[2])
        print("terminology config file directory path is invalid")
        print("Usage: rrfSampling.py <terminology RRF file path> <terminology config file path> <terminology>")
        return False
        
    return True

if __name__ == "__main__":

    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    
    if(checkParamsValid(sys.argv) == False):
        exit(1)
    
    terminology = sys.argv[3].upper()
    terminologyFileName = terminology.lower()
        
    configFile = open(sys.argv[2] + "/" + terminologyFileName + ".json")
    configData = json.load(configFile)
    
    with open(terminologyFileName + "-samples.txt", "w") as termFile:
    
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
                
                    conceptInfo = {"code": mrconsoCode, "termType": mrconsoTermType, "term": mrconsoTerm}
                    auiCodeMappings[mrconsoAui] = conceptInfo
                
                if(synonymPrinted == False): # print the first synonym
                
                    synonymPrinted = True
                    termFile.write(mrconsoCode + "\t" + mrconsoCode + "\t" + "synonym"  + "\t" + mrconsoTerm + "\n")
                    
                if(mrconsoTermType not in seenTypes): # print this term type if never seen
                
                    seenTypes.append(mrconsoTermType)
                    termFile.write(mrconsoCode + "\t" + mrconsoCode + "\t" + "term-type" + "\t" + mrconsoTermType + "\n")
            
        with open (sys.argv[1] + "/MRSAT.RRF", "r", encoding='utf-8') as mrsatFile:
        
            mrsatLines = mrsatFile.readlines()
        
            for mrsatIndex, mrsatLine in enumerate(mrsatLines): # get index just in case
                   
                mrsatLine = mrsatLine.strip() # no need for leading spaces anymore
                splitLine = mrsatLine.split("|")
                lineId = splitLine[3]
                lineSType = splitLine[4]
                lineAtn = splitLine[8]
                lineAtv = splitLine[10]
                
                if(lineAtn == 'SUBSET_MEMBER' or lineAtn == "CHARACTERISTIC_TYPE_ID" or lineAtn == "MODIFIER_ID"): # do not process these 
                    continue
                
                if(lineSType == 'RUI'): # handle RUIs specially
                    
                    if(lineAtn not in seenRuiAtns): # if this RUI ATN has not been seen save info for MRREL
                    
                        seenRuiAtns.append(lineAtn)
                        ruiAtns = []
                    
                        if(lineId in mrsatRuiAtnInfo):
                            ruiAtns = mrsatRuiAtnInfo[lineId]
                            
                        atnInfo = {"atn": lineAtn, "atv": lineAtv}
                        ruiAtns.append(atnInfo)
                        mrsatRuiAtnInfo[lineId] = ruiAtns
                     
                elif(lineSType == 'AUI'): # handle AUIs specially
                    
                    if(lineId not in auiCodeMappings): # must be from the terminology being processed 
                        continue
                    
                    code = auiCodeMappings[lineId]["code"]                    
                    synonymType = auiCodeMappings[lineId]["termType"]
                    
                    if (synonymType + lineAtn not in seenSynonymTypeAtns):
                    
                        seenSynonymTypeAtns.append(synonymType + lineAtn)
                        
                        qualifier = "qualifier-" + "synonym" + "~" + lineAtn
                        value = auiCodeMappings[lineId]["term"] + "~" + lineAtv
                        
                        termFile.write(code + "\t" + code + "\t" + qualifier + "\t" + value + "\n")
                    
                else: # handle everything else
                
                    if(lineId not in auiCodeMappings): # must be from the terminology being processed 
                        continue
                    
                    code = auiCodeMappings[lineId]["code"]
                
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
                
                code = auiCodeMappings[lineAui]["code"]
                    
                if(not defintionFound): # print this defintion if we haven't printed one
                
                    defintionFound = True
                    termFile.write(code + "\t" + code + "\t" + "DEFINITION" + "\t" + lineDef + "\n")
                    
        with open (sys.argv[1] + "/MRREL.RRF", "r", encoding='utf-8') as mrrelFile:
        
            mrrelLines = mrrelFile.readlines()
        
            for mrrelIndex, mrrelLine in enumerate(mrrelLines): # get index just in case
                   
                mrrelLine = mrrelLine.strip() # no need for leading spaces anymore
                splitLine = mrrelLine.split("|")
                lineAui1 = splitLine[1]
                lineRel = splitLine[3]
                lineAui2 = splitLine[5]
                lineRela = splitLine[7]
                lineRui = splitLine[8]
                
                if(lineAui2 not in auiCodeMappings or lineAui1 not in auiCodeMappings): # AUIs must be from the terminology being processed 
                    continue
                    
                if (lineAui1 not in listAui1):
                    listAui1.append(lineAui1)
                
                if (lineAui2 not in listAui1):
                    listAui2.append(lineAui2)
                    
                if (lineRel == "PAR"):
                    
                    auiParents = {"count": 0, "parentAuis": []}
                    
                    if (lineAui1 in auiNumberParents): # get any existing parent info
                        auiParents = auiNumberParents[lineAui1]
                    
                    if (lineAui2 not in auiParents["parentAuis"]):
                    
                        auiParents["count"] += 1
                        auiParents["parentAuis"].append(lineAui2)
                        auiNumberParents[lineAui1] = auiParents
                        
                if(lineRui in mrsatRuiAtnInfo): # must be in MRSAT
                    
                    code1 = auiCodeMappings[lineAui1]["code"]
                    code2 = auiCodeMappings[lineAui2]["code"]
                    
                    for atnInfo in mrsatRuiAtnInfo[lineRui]: #go thru all ATN entries for this RUI
                    
                        key = "qualifier-" + lineRel + "~" + atnInfo["atn"]
                        termFile.write(code2 + "\t" + code2 + "\t" + key + "\t" + atnInfo["atv"] + "\n")
                    
                        if(lineRela not in seenRelas and lineRela != ""): # print this relationship if RELA never seen and has a RELA 
                        
                            seenRelas.append(lineRela)
                            key = "qualifier-" + lineRel + "~RELA"
                            termFile.write(code2 + "\t" + code2 + "\t" + key + "\t" + lineRela + "\n")
                            
                    if(lineRel not in seenRels and lineRel != "PAR" and lineRel != "CHD"): # print this association if REL never seen
                    
                        seenRels.append(lineRel)
                        termFile.write(code2 + "\t" + code2 + "\t" + lineRel + "\t" + code1 + "\n")
                        
        rootAuis = [x for x in listAui1 if x not in listAui2] # any aui 1 not in aui2 is a root concept
        
        for rootAui in rootAuis: # print out root concepts
        
            code = auiCodeMappings[rootAui]["code"]
            termFile.write(code + "\t" + code + "\t" + "root" + "\n")
            
        for childAui, parentInfo in auiNumberParents.items():
            
            if (str(parentInfo["count"]) not in parentCountsSeen):
            
                parentCountsSeen.append(str(parentInfo["count"]))
                code = auiCodeMappings[childAui]["code"]
                termFile.write(code + "\t" + code + "\t" + "parent-count" + str(parentInfo["count"]) + "\n")
                
    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    