from datetime import datetime
import os
import re
import sys

def checkParamsValid(argv):
    if(len(argv) != 3):
        print("Usage: owlQA.py <terminology owl file path> <terminology json file path>")
        return False
    elif(os.path.isfile(argv[1]) == False or argv[1][-4:] != ".owl"):
        print(argv[1][-4:])
        print("terminology owl file path is invalid")
        print("Usage: owlQA.py <terminology owl file path> <terminology json file path>")
        return False
    elif(os.path.isfile(argv[2]) == False or argv[2][-5:] != ".json"):
        print("terminology json file path is invalid")
        print("Usage: owlQA.py <terminology owl file path> <terminology json file path>")
        return False
    return

def checkForNewStuff(properties, propertiesCurrentClass, line, currentCode, currentURI):
    splitLine = re.split("[<>= \"]", line.strip()) # split by special characters
    splitLine = [x for x in splitLine if x != ''] # remove empty entries for consistency
    if(splitLine[0] in properties or splitLine[0] in propertiesCurrentClass): # check duplicates
        return ""
    detail = ""
    if("rdf:resource=\"" in line): # grab stuff in quotes
        detail = re.findall('"([^"]*)"', line)[0]
    else: # grab stuff in tag
        detail = re.findall(">(.*?)<", line)[0]
    return (splitLine[0], currentURI + "\t" + currentCode + "\t" + splitLine[0] + "\t" + detail + "\n")


if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    
    if(checkParamsValid(sys.argv) == False):
        exit(1)
    with open (sys.argv[1], "r", encoding='utf-8') as owlFile:
        ontoLines = owlFile.readlines()
    terminology = sys.argv[1].split("/")[-1].split(".")[0]

    inClass = False
    inAxiom = False
    inSubclass = False
    currentURI = ""
    currentCode = ""
    properties = {} # master list
    propertiesCurrentClass = {} # current class list
    newEntry = ""
    
    with open(terminology + "_QA_OWL.txt", "w") as goFile:
        for line in ontoLines:
            line = line.strip()
            if(len(line) < 1 or line[0] != '<'): # blank lines or random text
                pass
            elif(line.startswith("<owl:deprecated")): # ignore deprecated classes
                inClass = False
                propertiesCurrentClass = {}
            elif(line.startswith("<owl:Class ")):
                inClass = True
                propertiesCurrentClass = {} # reset for new class
                currentURI = re.findall('"([^"]*)"', line)[0] # set uri entry in line
                currentCode = re.split("/", currentURI)[-1] # set temporary code entry in line
            elif(line.startswith("</owl:Class>")):
                for key, value in propertiesCurrentClass.items(): # replace code entry and write to file
                    properties[key] = value # add to master list
                    splitLineTemp = value.split("\t") # split to get code isolated
                    splitLineTemp[1] = currentCode # replace code
                    goFile.write("\t".join(splitLineTemp)) # rejoin and write
                inClass = False
            elif(line.startswith("<owl:Axiom>")):
                inAxiom = True
            elif(line.startswith("</owl:Axiom>")):
                inAxiom = False

            elif((line.startswith("<rdfs:subClassOf>") or line.startswith("<owl:equivalentClass>")) and not line.endswith("//>\n")): # inelegant way of skipping complex subclass            
                inSubclass = True
            elif(line.startswith("</rdfs:subClassOf>") or (line.startswith("</rdfs:equivalentClass>"))):
                inSubclass = False
            elif(inSubclass):
                pass

            elif(inClass and not inSubclass):
                if(line.startswith("<oboInOwl:id") and propertiesCurrentClass != {}): # catch ID to return if it has properties
                    currentCode = re.findall(">(.*?)<", line)[0]
                    continue
                newEntry = checkForNewStuff(properties, propertiesCurrentClass, line, currentCode, currentURI)
                if(len(newEntry) > 1 and newEntry[0] not in properties): # returned new property
                    propertiesCurrentClass[newEntry[0]] = newEntry[1] # add to current class property list
                newEntry = ""

    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    