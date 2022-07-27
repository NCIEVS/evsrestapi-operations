CTRP

What and Why

The Clinical Trials Reporting System (CTRP) allows for clinical trials to be submitted to a database, coded with NCIt terms, then made searchable on the clinicaltrials.gov website. On occasion a new trial will come in with terms that are not already in NCIt. New terms will then be requested, but will need to be present in NCIt before they can be used in the clinicaltrials.gov search.  Therefore CTRP needs an expedited release schedule, which Stardog supports.

Right now the editors export a new NCIt baseline weekly and place it on the group drive under P5_baselines.  This directory is accessible from the processing server at /p5_baselines. The plan is to eventually make this release daily.  For now, copy the file from /p5_baselines to Processing_Data and run the MasterCTRP.sh, passing in the asserted file name.

./MasterCTRP.sh Thesaurus-yymmdd-yy.mmv.owl 

Currently the MasterCTRP.sh does the following functions
1. Creates inferred version of the file
2. Run the file through OWLScrubber using the forProduction config files
3. Run through SedScript configured to create a fully byCode file (none of the LexEVS tweaks)
4. Zip the file
5. Copy the file to Amazon Web Services for use by the AWS Stardog

Manual steps to load to local Stardog (will be automated)
1. Copy the final zip file to the Stardog server (ncias-q1761-v.nci.nih.gov) ~/data-loads directory and unzip it
2. Change directory to /loca/content/triplestore/stardog/bin 
3. Remove the old graph - "./stardog data remove -g http://NCIt CTRP  -u <username> -p <password>"
4. Load the new version - "./stardog data add CTRP -g http://NCIt ~/data-loads/<owl-file> -u <username> -p <password>"
5. Put in data promotion request to Stage and Prod.

Manual steps to support NG browser development (Might be temporary so not automated yet)
1. Copy the final zip to the temp directory on SFTP
2. Delete previous versions of the zip
3. Send NG developers a link to the SFTP file (John C, Ruth M, Kim O, Jason L) 

Planned features for MasterCTRP.sh:
1. automation to copy zip to Stardog QA server
2. Adjusted version of ProtegeKbQA that gives a single up or down result, in addition to regular report
3. Have script NOT do uploads to AWS or elsewhere if automated QA fails
4. Notify EVS Ops if QA fails so they can review QA report.
5. Delete QA reports older than X days
6. Stop process and notify EVS Ops if any part of the MasterCTRP fails
7. Once all safeguards trusted, have the whole script run as a cron job.

Planned new script on Stardog server:
1. Detect when new file uploaded for processing server
2. Unzip file 
3. Unload old graph
4. Load new graph
5. Detect and report any errors with load
6. Notify Ops to request data promotion if load is error free.
7. Eventually have data promotion automatic by cron job.
