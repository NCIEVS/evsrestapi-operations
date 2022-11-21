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

def checkForNewStuff(coolStuff, line, currentCode, currentURI):
    splitLine = re.split("[<>= \"]", line.strip())
    splitLine = [x for x in splitLine if x != '']
    if(splitLine[0] in coolStuff):
        return ""
    detail = ""
    if("rdf:resource=\"" in line):
        detail = re.findall('"([^"]*)"', line)[0]
    else:
        detail = re.findall(">(.*?)<", line)[0]
    return (splitLine[0], currentURI + "    " + currentCode + " " + splitLine[0] + "    " + detail + "\n")


if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    print("")
    if(checkParamsValid(sys.argv) == False):
        exit(1)
    owlFile = open(sys.argv[1], "r")
    ontoLines = owlFile.readlines()

    inClass = False
    inAxiom = False
    inSubclass = False
    currentURI = ""
    currentCode = ""
    coolStuff = {}
    newEntry = ""
    with open("Go_QA_OWL.txt", "w") as goFile:
        for line in ontoLines:
            if(not line[0:4].isspace()): # skip random text lines
                pass
            elif(line.startswith("    <owl:Class ")):
                inClass = True
                currentURI = re.findall('"([^"]*)"', line)[0]
                currentCode = re.split("/", currentURI)[-1]
            elif(line.startswith("    </owl:Class>")):
                inClass = False
            elif(line.startswith("    <owl:Axiom>")):
                inAxiom = True
            elif(line.startswith("    </owl:Axiom>")):
                inAxiom = False

            elif((line.startswith("        <rdfs:subClassOf>") or line.startswith("        <owl:equivalentClass>")) and not line.endswith("//>\n")): # inelegant way of skipping complex subclass            
                inSubclass = True
            elif(line.startswith("        </rdfs:subClassOf>") or (line.startswith("        </rdfs:equivalentClass>"))):
                inSubclass = False
            elif(inSubclass):
                pass

            elif((inClass or inAxiom) and not inSubclass):
                newEntry = checkForNewStuff(coolStuff, line, currentCode, currentURI)
                if(newEntry != "" and newEntry[0] not in coolStuff):
                    coolStuff[newEntry[0]] = newEntry[1]
                    goFile.write(newEntry[1])
                newEntry = ""

    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    