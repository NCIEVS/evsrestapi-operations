---
name: evsrestapi-operations-deploy
description: Use when working in the NCIEVS evsrestapi-operations repository and the user asks to build the operations zip, create or replace a release tag, or deploy the operations artifact to EVS dev or QA through Jenkins AWS jobs.
---

# EVSRESTAPI Operations Deploy

Use this skill only for the `NCIEVS/evsrestapi-operations` repo.

## Jenkins Credentials

Before calling Jenkins, find credentials in environment variables. Do not print secret values.

1. Load shell profile variables first:

```bash
zsh -lc 'source ~/.zprofile 2>/dev/null || true; env | cut -d= -f1 | sort | grep -i jenkins || true'
```

2. Identify complete credential sets. Known working set for this repo:

```text
NCI_JENKINS_URL
NCI_JENKINS_USER
NCI_JENKINS_API_TOKEN
```

Also consider conventional complete sets such as:

```text
JENKINS_URL + JENKINS_USER + JENKINS_API_TOKEN
JENKINS_URL + JENKINS_USER + JENKINS_TOKEN
```

3. If multiple complete Jenkins credential sets are present, ask the user which one to use.
4. If no complete Jenkins credential set is present, stop and ask the user to set Jenkins URL, username, and API token environment variables.
5. Assign the selected values to local shell variables for commands in that run:

```bash
JENKINS_BASE_URL="https://evs-jenkins.nci.nih.gov/jenkins"
JENKINS_AUTH_USER="$NCI_JENKINS_USER"
JENKINS_AUTH_TOKEN="$NCI_JENKINS_API_TOKEN"
```

Memory from prior successful session: credentials were loaded from `~/.zprofile` using `NCI_JENKINS_USER` and `NCI_JENKINS_API_TOKEN`. The Jenkins API base was `https://evs-jenkins.nci.nih.gov/jenkins/`.

## User Choices

Ask the user before starting:

- Whether to create a new release tag and deploy, or deploy the most recent tag.
- Whether to deploy to `dev`, `qa`, or both.

Use the user's choices for the workflow. Do not assume a target environment.

## Tag Flow

Always fetch tags first so "most recent" is current:

```bash
git fetch --tags --prune origin
```

If deploying the most recent tag, use tag creation date:

```bash
git for-each-ref --sort=-creatordate --count=1 refs/tags --format='%(refname:short)'
```

If creating a tag:

1. Determine the Makefile-generated tag name:

```bash
VERSION=$(awk -F= '/^VERSION=/{print $2}' Makefile)
TAG="v$(date +%Y-%m-%d)-${VERSION}.RELEASE"
```

2. Check whether it already exists after fetching tags:

```bash
git rev-parse -q --verify "refs/tags/$TAG"
```

3. If the tag exists, ask whether to replace it.
4. If replacing, run:

```bash
make rmtag
make tag
```

5. If the tag does not exist, run:

```bash
make tag
```

The Makefile pushes the tag to `origin`.

## Jenkins Jobs

Build job:

```text
https://evs-jenkins.nci.nih.gov/jenkins/job/_default/job/_lower/job/_Evsrestapi/job/operations_build_AWS/
```

Dev deploy job:

```text
https://evs-jenkins.nci.nih.gov/jenkins/job/_default/job/_lower/job/_Evsrestapi/job/operations_deploy_dev_AWS/
```

QA deploy job:

```text
https://evs-jenkins.nci.nih.gov/jenkins/job/_default/job/_lower/job/_Evsrestapi/job/operations_deploy_qa_AWS/
```

Before triggering a job, read its parameter schema:

```bash
curl -sS -u "$JENKINS_AUTH_USER:$JENKINS_AUTH_TOKEN" "$JOB_URL/api/json?tree=name,url,buildable,nextBuildNumber,property%5BparameterDefinitions%5Bname,type,description,defaultParameterValue%5Bvalue%5D,choices%5D%5D"
```

## Build Workflow

Trigger the build with the release tag:

```bash
curl -i -X POST -u "$JENKINS_AUTH_USER:$JENKINS_AUTH_TOKEN" \
  --data-urlencode "BRANCH_OR_TAG=$TAG" \
  --data-urlencode "debug=false" \
  "$BUILD_JOB_URL/buildWithParameters"
```

Use the `Location` response header to poll the queue item:

```bash
curl -sS -u "$JENKINS_AUTH_USER:$JENKINS_AUTH_TOKEN" "$QUEUE_URL/api/json"
```

When `.executable.url` and `.executable.number` are set, poll the build:

```bash
curl -sS -u "$JENKINS_AUTH_USER:$JENKINS_AUTH_TOKEN" "$BUILD_URL/api/json?tree=building,result,number,url,displayName,artifacts%5BfileName,relativePath%5D"
```

Continue only if the build result is `SUCCESS`.

## Deploy Workflow

The deploy jobs copy artifacts from `operations_build_AWS` using their `BUILD_TAG_OR_BRANCH` parameter. This parameter must be the successful build display name, not just the tag.

Correct value format:

```text
<build_number>::<tag>
```

Example from prior successful session:

```text
143::v2026-06-05-2.4.0.RELEASE
```

Prefer reading `.displayName` from the successful build API response and passing that exact value.

Important learning: passing only `v2026-06-05-2.4.0.RELEASE` to `BUILD_TAG_OR_BRANCH` caused Jenkins to store the extended-choice parameter as empty and the deploy failed immediately in CopyArtifact with:

```text
java.lang.NumberFormatException: For input string: ""
```

Trigger each selected deploy job:

```bash
curl -i -X POST -u "$JENKINS_AUTH_USER:$JENKINS_AUTH_TOKEN" \
  --data-urlencode "BUILD_TAG_OR_BRANCH=$BUILD_DISPLAY_NAME" \
  --data-urlencode "debug=false" \
  --data-urlencode "remote=$REMOTE" \
  --data-urlencode "remote_user=$REMOTE_USER" \
  "$DEPLOY_JOB_URL/buildWithParameters"
```

Use the deploy job's default `remote` and `remote_user` values from the parameter schema unless the user requested overrides.

Poll deploy queue and build results the same way as the build job. Report each Jenkins build number, URL, and result.

## Failure Handling

- If Jenkins returns a login page or anonymous permission error, credentials were not applied correctly; re-check loaded environment variables.
- If a deploy fails immediately, read `consoleText` and verify `BUILD_TAG_OR_BRANCH` was the build display name.
- If build fails, do not deploy; report the build URL and the relevant console output.
