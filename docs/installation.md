---
layout: default
title: Installation & Usage
nav_order: 3
---
# Installation

```
git clone <tranql repository>
cd tranql
pip install -r tranql/requirements.txt
cd web
npm install
cd ../
```

# Running TranQL

## Backplane
```
# /tranql/backplane
PYTHONPATH=$PWD/../../ python server.py
```
Runs the backplane server on [localhost:8099](http://localhost:8099). Docs can be accessed with the [/apidocs](http://localhost:8099/apidocs) endpoint.

## API (requires backplane)
```
# /tranql/
PYTHONPATH=$PWD/../ python api.py
```
Runs the API on [localhost:8001](http://localhost:8001). Docs can be accessed with the [/apidocs](http://localhost:8001/apidocs) endpoint.

## Web App (requires API and backplane)
```
# /web/
npm start
```
This will run the web app on [localhost:3000](http://localhost:3000).

## Testing
```
# /
PYTHONPATH=$PWD pytest tranql/tests
```
