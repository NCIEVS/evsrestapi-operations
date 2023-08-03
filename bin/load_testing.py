#!/usr/bin/python
from datetime import datetime
import json
import os
import re
import sys
import random
import concurrent.futures
import threading
import requests
import time
import argparse
import statistics 

# The time interval in milliseconds between subsequent calls. 0 runs everything simultaneously.
timeBetweenCalls = 0;

# The number of calls to make.
numberOfCalls = 10;

# the base URL for the app 
appBaseUrl = "http://localhost:4200/api/v1/"

fullConceptURL = appBaseUrl + "concept/ncim/C0005768?include=full"
fullConceptTaskName = "fullConcept"
conceptSearchURL = appBaseUrl + "concept/search?terminology=ncit&include=summary,highlights,properties&term=dis&type=contains&export=false&fromRecord=0&pageSize=1000"
conceptSearchTaskName = "conceptSearch"
mapListURL = appBaseUrl + "mapset/SNOMEDCT_US_2020_09_01_to_ICD10CM_2021_Mappings/maps?pageSize=1000&fromRecord=0"
mapListTaskName = "mapList"
taxonomyURL = appBaseUrl + "concept/ncit/C16956/subtree/children?limit=100"
taxonomyTaskName = "taxonomy"
subsetListURL = appBaseUrl + "subset/ncit?include=full"
subsetListTaskName = "subsetList"
tests = [fullConceptTaskName, conceptSearchTaskName, mapListTaskName, taxonomyTaskName, subsetListTaskName]
timeMap = {}
callsCompleted = 0
totalCalls = 0
lock = threading.Lock()

def currentMilliseconds():
    return int(datetime.now().timestamp() * 1000)

def checkParamsValid(argv):

    global appBaseUrl, timeBetweenCalls, numberOfCalls
    
    parser = argparse.ArgumentParser(
                    prog='LoadTests',
                    description='Load Testing')
                    
    parser.add_argument("appBaseUrl", nargs='?', default="http://localhost:4200/api/v1/", help='the base URL for the app')                 
    parser.add_argument("timeBetweenCalls", nargs='?', default=timeBetweenCalls, help='The time interval in milliseconds between subsequent calls. 0 runs everything simultaneously')                 
    parser.add_argument("numberOfCalls", nargs='?', default=numberOfCalls, help='The number of calls to make')                            
    args = parser.parse_args()

    appBaseUrl = args.appBaseUrl
    timeBetweenCalls = int(args.timeBetweenCalls)
    numberOfCalls = int(args.numberOfCalls)
        
    return True
    
def testApiCall(taskId, url, name):

    error = ""
    
    try:
    
        taskSart = currentMilliseconds()
        request = requests.get(url)
        result = request.json()
        
        if (request.status_code != 200):
            error = result.get('message')
            
    except Exception as e:
        error = e
    
    if (error == ""):
        timeMap[name + str(taskId)] = currentMilliseconds() - taskSart;
    else:
        timeMap[name + str(taskId)] = "ERROR: " + error;
        
    progressBar()
    
def testRun(executor, url, name):

    for i in range (numberOfCalls):
        
        future = executor.submit(testApiCall, i, url, name)
        # future.result()
        
        if(timeBetweenCalls > 0):
            time.sleep(timeBetweenCalls / 1000)
   
def progressBar():

    global callsCompleted, lock
    
    with lock:
        n_bar = 50  # Progress bar width
        callsCompleted = callsCompleted + 1
        progress = callsCompleted / totalCalls
        sys.stdout.write('\r')
        sys.stdout.write(f"[{'=' * int(n_bar * progress):{n_bar}s}] {int(100 * progress)}%  Progress")
        sys.stdout.flush()
    
if __name__ == "__main__":

    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    
    loadStart = currentMilliseconds()
    
    if(checkParamsValid(sys.argv) == False):
        exit(1)
        
    print("Params appBaseUrl: " + appBaseUrl)
    print("Params timeBetweenCalls: " + str(timeBetweenCalls))
    print("Params numberOfCalls: " + str(numberOfCalls))
    print("")
    
    totalCalls = numberOfCalls * len(tests)
    numberOfThreads = 100
    
    if (numberOfCalls > numberOfThreads):
        numberOfThreads = numberOfCalls
    

    with concurrent.futures.ThreadPoolExecutor(max_workers=numberOfThreads) as executor:

        testRun(executor, fullConceptURL, fullConceptTaskName)
        testRun(executor, conceptSearchURL, conceptSearchTaskName)
        testRun(executor, mapListURL, mapListTaskName)
        testRun(executor, taxonomyURL, taxonomyTaskName)
        testRun(executor, subsetListURL, subsetListTaskName)
    
    print("")
    #print("Timemap: ", timeMap)
    
    with open("load-test-run_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".txt", "w") as testFile:
    
        # print stats
        for test in tests:
        
            times = []
            errors = 0
            
            for i in range (numberOfCalls):
            
                index = str(i)
                value = timeMap[test + index]
                
                if (not str(value).startswith("ERROR")):
                    times.append(value)
                    
                else:
                    errors += 1
                    
                testFile.write(test + "\t" + index + "\t" + str(value) + "\n")
            
            if (len(times) > 0):
            
                print(test + " call minimum time taken: ", min(times))   
                print(test + " call maximum time taken: ", max(times))   
                print(test + " call average time taken: ", statistics.mean(times))   
                print(test + " call median time taken: ", statistics.median(times))  
                
            print(test + " call errors: ", errors)   
            print("")
        
    print("Load Test time taken: ", (currentMilliseconds() - loadStart))
    print("")
                
    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    