# TranQL

TranQL is a query language for interactive exploration of federated knowledge graphs.

## Background

Previous [work](https://github.com/NCATS-Tangerine/ros) focused on a workflow language for automating queries. We've also prototyped similar workflows using the [Common Workflow Language (CWL)](https://www.commonwl.org/).

Workflow languages generally provide capabilities to support large scale, fault tolerant, reproducible, automated computing. These are critical features where processes that have been refined by teams over time must be automated and shared. Common characteristics of these systems include:
  * The ability to **manage multiple, interacting, long running** third party programs (eg, genomic sequence alignment)
  * Infrastructure level support for **reproducibility** via highly technical artifacts like Docker containers.
  * **Complex syntax** in formats like YAML, which are generally unfamilar to clinical data and medical experts.

While these features are essential for some applications, they are neither targeted at nor well suited to
  * **Iterative, interactive exploration** of large data sets.
  * **Accessibility** to communities like clinical data specialists and medical experts.
  * **A programmatic interface between applications** and a data source.
  
## Interactive Exploration

The ability to explore large data sets with queries is extremely familiar to clinical data experts and many medical informatics specialists. To make semantic databases more accessible to these communities, we designed TranQL to share structural and syntactic similarities to the most familiar and widely used languages able to interact with distributed data sets.

In particular, the [Structured Query Language (SQL)](https://en.wikipedia.org/wiki/SQL) is among the most pervasive data query languages in use. It is vital to the work of clinical data specialists. TranQL borrows concepts from SQL while borrowing elements of graph semantics from query languages like [Cypher](https://neo4j.com/developer/cypher-query-language/).

It must be noted here that the [W3C Semantic Web](https://www.w3.org/standards/semanticweb/) stack has the most robust and mature toolkit in this space surrounding technologies  including RDF and SPARQL. However, wide spread adoption of this stack has not approached the levels of technologies like SQL, REST and OpenAPI. Also, the W3C stack envisions a heterogeneous RDF/SPARQL environment. We sought something able to embrace more heterogeneous data sources.

## Design Overview

### Language

TranQL is a classic interpreter with a lexical analyzer & parser which produces token stream. The tokens are interpreted to build an abstract syntax tree modeling the program's constructs which are then executed sequentially. It supports three statement types:
  * **SET**: Assign a value to a variable.
    - ```
       SET <variable> = <value>
      ```
  * **SELECT**: Select a graph described by a pattern from a service, given various constraints. Graphs patterns are expressed using concepts from the biolink-model.
    - ```
       SELECT <graph> 
       FROM <service> 
       [WHERE <constraint> [AND <constraint]*]
       [[SET <jsonpath> AS <var> | [SET <var>]]*```
  * **CREATE GRAPH**: Create a graph at a service.
    - ```
       CREATE GRAPH <var> AT <service> AS <name>
      ```

## Standard API

The [Translator standard graph API](https://github.com/NCATS-Gamma/NCATS-ReasonerStdAPI) is a protocol for exchanging graphs with federated data sources. TranQL works with endpoints supporting this standard.

## Backplane
 
The TranQL Backplane is a collection of endpoints supporting the standard API which implement reusable question answering services, or modules.

Backplane modules support a simplified syntax in the language for greater readability.

## Example

#### The Comment

The example program begins with a multi-line comment describing its intent:

![image](https://user-images.githubusercontent.com/306971/52903897-53d7a980-31f2-11e9-8d43-538ee2d44ad3.png)

#### The First Select Statement

The first statement **selects a graph pattern** connecting disease nodes to chemical substances, both `biolink-model` concepts.

![image](https://user-images.githubusercontent.com/306971/52904001-9d74c400-31f3-11e9-8ea9-9362de79523b.png)

The **from clause** specifies the path to a Backplane endpoint. Because it begins with a "/", TranQL prepends the protocol, host, and port of a configured TranQL Backplane service. The service can be any endpoint implementing the standard graph endpoint interface.

The first **`where` constraint** parameterizes the disease question node sent to the service. In this case, it resolves an English word into ontology identifiers using the [bionames](https://bionames.renci.org/apidocs/) API. If curies are supplied, those are used directly.

The rest of the constraints, because they do not map to graph query elements, are **transmitted to the service as `options`** in the standard protocol. The service being invoked validates and interprets the options. In the case above, the endpoint passes the options along to define a cohort in the ICEES clinical reasoner.

The final part of the select statement is a `set` statement which **uses a JSONPath query to extract chemical identifiers** from the result, store them as a variable.

#### The Second Select Statement

The second `select` statement sends a different graph query to the Gamma reasoner and parameterizes the chemical_substance concept with identifiers from the first clinical step.

![image](https://user-images.githubusercontent.com/306971/52903985-7ddd9b80-31f3-11e9-9caf-ebcf96f84fc0.png)

The resulting **graph is saved as a variable**.

#### Publishing to Visualizers

The Backplane implements two standard API endpoint for publishing the graph for visualization. One supports the UCSD NDEx network sharing platform and the other supports Gamma's answer visualisation facility.

![image](https://user-images.githubusercontent.com/306971/52903927-b9c43100-31f2-11e9-992e-11161e438a8b.png)

The program ends by publishing the answer set to both services.

##### NDEx:

![image](https://user-images.githubusercontent.com/306971/52904073-95695400-31f4-11e9-9b1d-bfba64e532b7.png)

##### Gamma:

![image](https://user-images.githubusercontent.com/306971/52904079-c5185c00-31f4-11e9-88bc-54e745c0c216.png)

Here's a [link to the Gamma visualization for the answer](http://robokop.renci.org/simple/view/918894c4-e21d-4901-a0c9-a2fa291ba381).

## Status

TranQL is brand new and strictly alpha. 

## Installation and Usage

### Install:
```
git clone <repository>
cd tranql
pip install -r tranql/requirements.txt
```
### Test
```
bin/test --capture=no
```
### Run

Run a program.
```
bin/tranql --source tranql/workflows/workflow-5.tranql
```
### Shell

Run the interactive interpreter.
```
bin/tranql --shell
```
### Options
```
$ bin/tranql --help
usage: main.py [-h] [-d] [-c] [-b BACKPLANE] [-i] [-s SOURCE]

TranQL

optional arguments:
  -h, --help                           show this help message and exit
  -d, --verbose                        Verbose mode. (default: False)
  -c, --cache                          Cache. (default: False)
  -b BACKPLANE, --backplane BACKPLANE  Backplane URL prefix (default:
                                       http://localhost:8099)
  -i, --shell                          The interpreter read-eval-print-loop
                                       (REPL). (default: False)
  -s SOURCE, --source SOURCE           The program's source file (default:
                                       None)
```
## Next

  * [Done] Move to the latest standard API version (0.9.0)
  * [Done] Implement basic NDEx visualization connectivity
  * [Done] Implement basic Gamma visualization connectivity
  * Handle mappings from the standard API
  * Model queries with predicates
  * Validate queries against the biolink-model
  * Add export to and possible integration with Neo4J
  * A graph [metadata API](http://robokop.renci.org/api/operations) would let users know which queries are possible.
