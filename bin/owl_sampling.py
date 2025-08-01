#!/usr/bin/python
from datetime import datetime
import json
import os
import re
import sys

oboURL = "http://purl.obolibrary.org/obo/"
oboPrefix = False
inAxiom = False
inClass = False
inRestriction = False
inSubclass = False
inEquivalentClass = False
inObjectProperty = False
inAnnotationProperty = False
currentClassURI = ""
currentClassCode = ""
currentClassPath = []
classHasCode = False # check for deprecated classes having a concept code
lastSpaces = 0
spaces = 0
axiomInfo = [] # key value pair storing info about current axiom
properties = {} # master list
axiomProperties = {} # list of axiom properties
objectProperties = {} # list of object properties
annotationProperties = {} # list of annotationProperties
propertiesMultipleSamples = {} # properties that should show multiple examples
propertiesMultipleSampleCodes = ['P310'] # the codes that should work with multiple samples
propertiesCurrentClass = {} # current class list
propertiesParentChilden = {} # parent/child list
parentStyle1 = [] # parent, child key value pair for subclass parent
parentStyle2 = [] # parent, child key value pair for rdf:description parent
uri2Code = {} # store ID codes for each URI when processed
uriRestrictions2Code = {} # separately store restriction codes so they don't get processed as roots
allParents = {} # all parent to children relationships
allChildren = {} # all children to parent relationships
parentCount = {} # list of parent count codes from 1 to n
deprecated = {} # list of all deprecated concepts
newRestriction = "" # restriction code
hitClass = False # ignore axioms and stuff before hitting any classes
termCodeline = "" # terminology Code identifier line
uniquePropertiesList = [] # store potential synonym/definition metadata values
dataPropertiesList = [] # hold list of data properties
inComplexProperty = 0 # skip complex properties
buildingProperty = "" # catch for badly formatted multi line properties
termJSONObject = "" # terminology properties
inComplexAxiom = False # complex axiom handling (skipping)
inIndividuals = False # skip individuals section
inDataProperties = False # get data properties to skip
inNoCodeClass = False # no code class handling (skipping)

def checkParamsValid(argv):
    if(len(argv) != 3):
        print("Usage: owl_sampling.py <terminology owl file path> <terminology json path>")
        return False
    elif(os.path.isfile(argv[1]) == False or argv[1][-4:] != ".owl" or argv[2][-5:] != ".json"):
        print(argv[1][-4:])
        print("terminology owl file path is invalid")
        print("Usage: owl_sampling.py <terminology owl file path> <terminology json path>")
        return False
    return True

def parentChildProcess(line):
    uriToProcess = re.findall('"([^"]*)"', line)[0]
    if(line.startswith("<rdfs:subClassOf rdf:resource=")):
        if(parentStyle1 == []): # first example of rdf:subClassOf child
            parentStyle1.append((currentClassURI, uriToProcess)) # hold in the parentStyle1 object as tuple
    elif(line.startswith("<rdf:Description") and inEquivalentClass):
        if(parentStyle2 == []): # first example of rdf:Description child
            parentStyle2.append((currentClassURI, uriToProcess)) # hold in the parentStyle2 object as tuple
            
    if(currentClassURI in allParents): # process parent relationship
        if(uriToProcess not in allParents[currentClassURI]): # avoid duplicates
            allParents[currentClassURI].append(uriToProcess)
    else:
        allParents[currentClassURI] = [uriToProcess]
        
    if(uriToProcess in allChildren): # process child relationship
        if(currentClassURI not in allChildren[uriToProcess]): # avoid duplicates
            allChildren[uriToProcess].append(currentClassURI)
    else:
        allChildren[uriToProcess] = [currentClassURI]
    return

def checkForNewProperty(line):
    if(line.endswith("/>") and not re.search(r'>.*?<', line) and not "owl:disjointWith" in line): # check for non-picked single-line properties
      return ""
    splitLine = re.split("[<>= \"]", line.strip()) # split by special characters
    splitLine = [x for x in splitLine if x != ''] # remove empty entries for consistency
    if(oboPrefix and splitLine[0].startswith(oboPrefix)):
      splitLine[0] = splitLine[0].replace(oboPrefix + ":", "")
    if(splitLine[0] in properties or splitLine[0] in propertiesCurrentClass): # check duplicates
        return ""
    detail = ""
    if(splitLine[0].startswith(terminology + ":")):
      splitLine[0] = splitLine[0].removeprefix(terminology + ":")
    if("rdf:resource=" in line and "http" in line): # grab link in quotes
        detail = re.findall('"([^"]*)"', line)[0]
    elif("rdf:resource=\"" in line): # grab stuff in quotes
        detail = re.split(r'[#/]', re.findall('"([^"]*)"', line)[0])[-1] # the code is the relevant part
    else: # grab stuff in tag
        detail_parts = re.findall(">(.+?)<", line)
        if detail_parts:
            detail = re.findall(">(.+?)<", line)[0]
    return (splitLine[0], currentClassURI + "\t" + currentClassCode + "\t" + splitLine[0] + "\t" + detail + "\n") # pound sign removal for ndfrt

def handleRestriction(line):
    global newRestriction # grab newRestriction global
    global dataPropertiesList # grab data properties list
    detail_parts = re.findall('"([^"]*)"', line)
    if not detail_parts:
        return
    detail = re.findall('"([^"]*)"', line)[0]
    pathCode = "/".join(currentClassPath) + "~" # prebuild tag stack for restriction
    property = re.split(r'[#/]', detail)[-1] # extract property
    if(property in dataPropertiesList): # ignore anything in dataPropertiesList
      return
    if(line.startswith("<owl:onProperty")): # property code
      if(detail in uri2Code):
        newRestriction = uri2Code[detail]
      else:
        newRestriction = property
            
    elif(line.startswith("<owl:someValuesFrom")): # value code
      if(newRestriction == "" or pathCode + newRestriction in uriRestrictions2Code): # duplicate
        return
      propertiesCurrentClass[pathCode+newRestriction] = currentClassURI + "\t" + currentClassCode + "\t" + pathCode+newRestriction + "\t" + detail.strip("#") + "\n" # add code/path to properties
      uriRestrictions2Code[pathCode+newRestriction] = newRestriction
      newRestriction = "" # saved code now used, reset to empty
            
def handleAxiom(line):
    global currentClassURI # grab globals
    global currentClassCode
    global inComplexAxiom
    if(line.startswith("<owl:annotatedSource")): # get source uri and code
        currentClassURI = re.findall('"([^"]*)"', line)[0]
    elif(line.startswith("<owl:annotatedProperty")): # get property code
        sourceProperty = re.findall('"([^"]*)"', line)[0]
        if(sourceProperty.find("oboInOwl#") != -1):
          axiomInfo.append("qualifier-" + re.split(r'[/]', sourceProperty)[-1].replace("#", ":") + "~")
        elif(sourceProperty.find("rdf-schema#") != -1):
          axiomInfo.append("qualifier-" + re.split(r'[/]', sourceProperty)[-1].replace("rdf-schema#", "rdfs:") + "~")
        else:
          axiomInfo.append("qualifier-" + re.split(r'[#/]', sourceProperty)[-1] + "~")
    elif(line.startswith("<owl:annotatedTarget>")): # skip complex axiom
        inComplexAxiom = True
        return
    elif(line.startswith("<owl:annotatedTarget")): # get target code
        axiomInfo.append(re.findall(">(.+?)<", line)[0] + "~")
    elif(not line.startswith("<owl:annotated") and len(re.split(r'[< >]', line)) > 1 and len(re.findall(">(.+?)<", line)) > 0 and axiomInfo[0] + re.split(r'[< >]', line)[1] + "~" + re.findall(">(.+?)<", line)[0] not in axiomProperties): # get connected properties
        newProperty = re.split(r'[< >]', line)[1] # extract property from line
        if(len(re.findall(">(.+?)<", line)) > 0):
          newCode = re.findall(">(.+?)<", line)[0] # extract code from line
        elif(len(re.findall('"([^"]*)"', line)) > 0 and len(re.split(r'[#/]', re.findall('"([^"]*)"', line)[0])) > 0): # check for quotes with a #
          newCode = re.split(r'[#/]', re.findall('"([^"]*)"', line)[0])[-1]
        else: # couldn't find any property codes so we skip
          return
        if(newProperty in uniquePropertiesList):
          newProperty += ("~" + newCode)
        axiomProperties[axiomInfo[0] + newProperty] = currentClassURI + "\t" + currentClassCode + "\t" + axiomInfo[0] + newProperty + "\t" + axiomInfo[1] + newCode + "\n"

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    
    if(checkParamsValid(sys.argv) == False):
        exit(1)
    with open (sys.argv[1], "r", encoding='utf-8') as owlFile:
        ontoLines = owlFile.readlines()
    terminology = sys.argv[2].split("/")[-1].split(".")[0]
    with open(sys.argv[2], "r", encoding='utf-8') as termJSONFile: # import id identifier line for terminology
      termJSONObject = json.load(termJSONFile)
      if(not termJSONObject["code"]):
        print("terminology json file does not have ID entry")
        termCodeline = "<owl:Class rdf:about"
      else:
        termCodeline = "<" + termJSONObject["code"] # data lines all start with #
      if("synonymSource" in termJSONObject): # get unique properties list (the ones we want to track all possible properties of for sampling)
        uniquePropertiesList.append(termJSONObject["synonymSource"])
      if("synonymTermType" in termJSONObject):
        uniquePropertiesList.append(termJSONObject["synonymTermType"])
      if("definitionSource" in termJSONObject):
        uniquePropertiesList.append(termJSONObject["definitionSource"])
      if("preferredName" in termJSONObject):
        uniquePropertiesList.append(termJSONObject["preferredName"])
      
    
    with open(terminology + "-samples.txt", "w") as termFile:
        for index, line in enumerate(ontoLines): # get index just in case
            #print(line + " " + str(index))
            lastSpaces = spaces # previous line's number of leading spaces (for comparison)
            spaces = len(line) - len(line.lstrip()) # current number of spaces (for stack level checking)
            line = line.strip() # no need for leading spaces anymore
            if(line.startswith("// Annotations")): # skip ending annotation
              hitClass = False
              continue
            elif(inNoCodeClass): # skip no code class
              if(line.startswith("</owl:Class>")):
                inNoCodeClass = False
              continue
            elif(inDataProperties and line.startswith("<!--") and not line.endswith(" -->")):
              inDataProperties = False
              continue
            elif(inDataProperties):
              if(line.startswith("<owl:DatatypeProperty ")):
                dataPropertiesList.append(line.split('/')[-1].split('"')[0])
              continue
            elif(line.startswith("// Data properties")):
              inDataProperties = True
              continue
            elif(line.startswith("<!--") or line.startswith("-->")): # skip concept titles
              continue
            elif(line.startswith("<owl:deprecated>false")):
              continue
            elif(buildingProperty != ""): # handling badly formatted multi-line properties
              buildingProperty += (" " + line)
              if(line.endswith(">")):
                line = buildingProperty
                buildingProperty = "" # end of the property
              else:
                continue
            elif(line.startswith("// Individuals") or inIndividuals): # skip everything past individuals
              inIndividuals = True
              continue
            # complex properties
            elif(inComplexProperty > 0 and (line.startswith("</owl:someValuesFrom>") or line.startswith("</owl:disjointWith>") or (line.startswith("</owl:Class>") or (line.startswith("</owl:allValuesFrom>")) and (inEquivalentClass or inSubclass)))):
              inComplexProperty -= 1
              continue
            elif(line.startswith("<owl:someValuesFrom>") or line.startswith("<owl:disjointWith>") or (line.startswith("<owl:Class>") or (line.startswith("<owl:allValuesFrom>")) and (inEquivalentClass or inSubclass))):
              inComplexProperty += 1
              continue
            # some parent relationships in complex properties
            elif(line.startswith("<rdfs:subClassOf ") or (line.startswith("<rdf:Description ") and inEquivalentClass)): # catch either example of parent/child relationship
                parentChildProcess(line)
            elif(inComplexProperty > 0):
              continue
            
            # end of complex properties
                
            elif(line.startswith("<owl:ObjectProperty") and not line.endswith("/>")):
              inObjectProperty = True;
              currentClassURI = re.findall('"([^"]*)"', line)[0]
            elif(line.startswith("</owl:ObjectProperty>")):
              inObjectProperty = False
            elif inObjectProperty and line.startswith(termCodeline):
              if(not line.endswith(">")): # badly formatted properties
                  buildingProperty = line
                  continue
              uri2Code[currentClassURI] = re.findall(">(.+?)<", line)[0]
              objectProperties[currentClassURI] = uri2Code[currentClassURI]
              
            elif(line.startswith("<owl:AnnotationProperty") and not line.endswith("/>")):
              if(not line.endswith(">")): # badly formatted properties
                  buildingProperty = line
                  inAnnotationProperty = True;
                  continue   
              inAnnotationProperty = True;
              currentClassURI = re.findall('"([^"]*)"', line)[0]
            elif(line.startswith("</owl:AnnotationProperty>")):
              inAnnotationProperty = False
            elif (inAnnotationProperty and line.startswith(termCodeline)):
              if(not line.endswith(">")): # badly formatted properties
                  buildingProperty = line
                  continue
              uri2Code[currentClassURI] = re.findall(">(.+?)<", line)[0]
              annotationProperties[currentClassURI] = uri2Code[currentClassURI]
            elif(line.startswith("<owl:AnnotationProperty")and line.endswith("/>")):
              annotationProperties[line.split("\"")[-2]] = line.split("\"")[-2].split("/")[-1]
              
            elif(line.startswith("xml") and oboURL in line): # handle obo prefixes
                oboPrefix = line.split(':')[1].split("=")[0] # get oboPrefix
            elif(len(line) < 1 or line[0] != '<'): # blank lines or random text
                continue
            elif(line.startswith("<owl:deprecated") and classHasCode is False): # ignore deprecated classes if they don't have a concept code
                inClass = False
                propertiesCurrentClass = {} # ignore properties in deprecated class
                deprecated[currentClassURI] = True
            elif(line.startswith("<owl:deprecated")): # track deprecated but still used classes for root filtering
                deprecated[currentClassURI] = False;
            # if no code after the pound sign, then there's no code and we skip it
            elif(line.startswith("<owl:Class ") and not inEquivalentClass and re.findall(r'"(.*?)"', line)[0].endswith("#")):
              inNoCodeClass = True # no code class
            elif(line.startswith("<owl:Class ") and not inEquivalentClass and not line.endswith("/>")):
              if not hitClass:
                hitClass = True
              inClass = True
              propertiesCurrentClass = {} # reset for new class
              currentClassURI = re.findall('"([^"]*)"', line)[0] # set uri entry in line
              currentClassCode = re.split("/|#", currentClassURI)[-1] # set initial class code
              uri2Code[currentClassURI] = currentClassCode # set initial uri code value
              continue
            elif(line.startswith("</owl:Class>") and not inEquivalentClass):
                for key, value in propertiesCurrentClass.items(): # replace code entry and write to file
                    if("hierarchyRoles" in termJSONObject and key.split("~")[-1] in termJSONObject["hierarchyRoles"]): # check for hierarchy roles
                      continue # skip hierarchy roles
                    properties[key] = value # add to master list
                inClass = False
                classHasCode = False # reset check for next deprecated class
                currentClassPath = []
                continue
                
            if(inClass and not inRestriction): # keep stack of current tree for restrictions (more/down level)
                if(spaces > lastSpaces): # add to stack based on spacing
                    currentClassPath.append(re.split(">| ", line)[0][1:])
                elif(lastSpaces > spaces): # remove from stack based on spacing (less/up level)
                    currentClassPath.pop()
                else: # replace in stack based on spacing (unchanged)
                    if(len(currentClassPath) > 0):
                      currentClassPath.pop()
                    currentClassPath.append(re.split(">| ", line)[0][1:])

            if((line.startswith("<rdfs:subClassOf>") and not line.endswith("//>\n"))): # find complex subclass            
                inSubclass = True
            elif(line.startswith("</rdfs:subClassOf>")) :
                inSubclass = False
            
            elif line.startswith("<owl:Axiom>") and hitClass: # find complex subclass            
                inAxiom = True
            elif line.startswith("</owl:Axiom>"):
                inComplexAxiom = False
                inAxiom = False
                axiomInfo = [] # empty the info list for the previous axiom
            elif inAxiom:
                if(not inComplexAxiom):
                    handleAxiom(line)
 
            elif(line.startswith("<owl:equivalentClass>")): # tag equivalentClass (necessary for restrictions)
                inEquivalentClass = True
            elif(line.startswith("</owl:equivalentClass>")) :
                inEquivalentClass = False
                continue
            
            elif(line.startswith("<rdfs:subClassOf") or (line.startswith("<rdf:Description ") and inEquivalentClass)): # catch either example of parent/child relationship
                parentChildProcess(line)
                            
            elif(inClass and line.startswith("<owl:Restriction>")):
                inRestriction = True
            elif(inClass and line.startswith("</owl:Restriction>")):
                inRestriction = False
            elif(inClass and inRestriction):
                handleRestriction(line)

            elif(inClass and not inSubclass and not inEquivalentClass): # default property not in complex part of class
                if(not line.endswith(">")):
                  buildingProperty = line
                  continue                 
                if(line.startswith(termCodeline)): # catch ID to return if it has properties
                    currentClassCode = re.findall(">(.+?)<", line)[0]
                    classHasCode = True
                    uri2Code[currentClassURI] = currentClassCode # store code for uri
                    continue
                newEntry = checkForNewProperty(line)
                if(len(newEntry) > 1 and newEntry[0] in propertiesMultipleSampleCodes): # handle multiple example codes
                    exampleCode = newEntry[1].split("\t")[-1][:-1] # extract code
                    if(exampleCode not in propertiesMultipleSamples):
                        propertiesMultipleSamples[exampleCode] = newEntry[1] # set value as key to avoid duplications
                elif(len(newEntry) > 1 and newEntry[0] not in properties): # returned new property
                    propertiesCurrentClass[newEntry[0]] = newEntry[1] # add to current class property list
                    
        for key, value in properties.items(): # write normal properties
            splitLineTemp = value.split("\t") # split to get code isolated
            splitLineTemp[1] = uri2Code[splitLineTemp[0]]
            if(splitLineTemp[2] in uri2Code):
              splitLineTemp[2] = uri2Code[splitLineTemp[2]]
            if(splitLineTemp[3] and splitLineTemp[3][:-1] in uri2Code): # deal with newline
              splitLineTemp[3] = uri2Code[splitLineTemp[3][:-1]] + "\n"
            termFile.write("\t".join(splitLineTemp)) # rejoin and write
            
        for key, value in propertiesMultipleSamples.items(): # write properties with multiple examples
            splitLineTemp = value.split()
            splitLineTemp[1] = uri2Code[splitLineTemp[0]]
            termFile.write("\t".join(splitLineTemp) + "\n") # rejoin and write
            
        for key, value in axiomProperties.items(): # write properties with multiple examples
            termFile.write(value) # rejoin and write
        
        if(parentStyle1 != []): # write out subclass parent/child
            termFile.write(parentStyle1[0][0] + "\t" + uri2Code[parentStyle1[0][0]] + "\t" + "parent-style1" + "\t" + uri2Code[parentStyle1[0][1]] + "\n")
            termFile.write(parentStyle1[0][0] + "\t" + uri2Code[parentStyle1[0][1]] + "\t" + "child-style1" + "\t" + uri2Code[parentStyle1[0][0]] + "\n")
        if(parentStyle2 != []): # write out relationship parent/child
            termFile.write(parentStyle2[0][0] + "\t" + uri2Code[parentStyle2[0][0]] + "\t" + "parent-style2" + "\t" + uri2Code[parentStyle2[0][1]] + "\n")
            termFile.write(parentStyle2[0][0] + "\t" + uri2Code[parentStyle2[0][1]] + "\t" + "child-style2" + "\t" + uri2Code[parentStyle2[0][0]] + "\n")
            
        maxChildren = ("", 0)
        for parent, children in allChildren.items(): # find maximum number of children
            if len(children) > maxChildren[1]: # update whenever we find a bigger child list
                maxChildren = (parent, len(children))
        if(maxChildren[1] > 0): # write that property to the file
            termFile.write(maxChildren[0] + "\t" + uri2Code[maxChildren[0]] + "\t" + "max-children" + "\t" + str(maxChildren[1]) + "\n")
        for child, parents in allParents.items(): # process parent counts
            if(len(parents) not in parentCount): # add new length example
                parentCount[len(parents)] = child
        for numParents in sorted(parentCount.keys()): # sort for writing to file
            termFile.write(parentCount[numParents] + "\t" + uri2Code[parentCount[numParents]] + "\t" + "parent-count" + str(numParents) + "\n")
            
        for code in uri2Code: # write out roots (all codes with no parents)
            if code not in allParents and code not in deprecated and code not in objectProperties and code not in annotationProperties.keys(): # deprecated codes, object properties, and annotation properties are fake roots
                termFile.write(code + "\t" + uri2Code[code] + "\t" + "root" + "\n")
            

    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
