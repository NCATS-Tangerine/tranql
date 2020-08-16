---
layout: default
title: Background
nav_order: 2
---
# Background

Previous [work](https://github.com/NCATS-Tangerine/ros) focused on a workflow language for automating biomedical queries. We've also [prototyped](https://github.com/NCATS-Tangerine/ros/blob/master/ros/wf5/workflow_5_main.cwl) similar workflows using the [Common Workflow Language (CWL)](https://www.commonwl.org/).

[Workflow languages](https://github.com/common-workflow-language/common-workflow-language/wiki/Existing-Workflow-systems) generally provide capabilities to support large scale, fault tolerant, reproducible, automated computing. These are critical features where processes that have been refined by teams over time must be automated and shared. Common characteristics of these systems include:
  * The ability to **manage multiple, interacting, long running** third party programs (eg, genomic sequence alignment)
  * Infrastructure level support for **reproducibility** via highly technical artifacts like Docker containers.
  * **Complex syntax** in formats like YAML, which are generally unfamilar to clinical data and medical experts.

While these features are essential for some applications, they are neither targeted at nor well suited to
  * **Iterative, interactive exploration** of large data sets.
  * **Accessibility** to communities like clinical data specialists and medical experts.
  * **A programmatic interface between applications** and a data source.

## Interactive Exploration

The ability to explore large data sets with queries is extremely familiar to clinical data experts and many medical informatics specialists. To make semantic databases more accessible to these communities, we designed TranQL to share structural and syntactic similarities with the most familiar and widely used languages for interactive distributed data analytics, while providing an interface to heterogeneous semantic graph services existing environments don't address.

In particular, the [Structured Query Language (SQL)](https://en.wikipedia.org/wiki/SQL) is among the most pervasive query languages in use. It is vital to the work of clinical data specialists. TranQL borrows concepts from SQL while borrowing elements of graph semantics from query languages like [Cypher](https://neo4j.com/developer/cypher-query-language/).

It must be noted here that the [W3C Semantic Web](https://www.w3.org/standards/semanticweb/) stack has the most robust and mature toolkit in this space surrounding technologies  including RDF and SPARQL. However, wide spread adoption of this stack has not approached the levels of technologies like SQL, REST and OpenAPI. Also, the W3C stack envisions a homogeneous RDF/SPARQL environment. We sought something able to embrace more heterogeneous data sources.

On a final contextual note, we've also evaluated a [GraphQL interface](https://mesostars.wordpress.com/2017/08/25/graphql-alpha/) to these federated data services. GraphQL, it's name not withstading, does not provide much in the way of constructs allowing the user to think explicitly in terms of a knowledge graph compared to Cypher or SPARQL. And, again, it's query syntax and approach is highly unfamiliar to clinical data and medical communities.

## Design

### Language

TranQL is a classic interpreter with a lexical analyzer & parser which produces a token stream. The tokens are interpreted to build an abstract syntax tree modeling the program's constructs which are then executed sequentially. The grammar supports three types of statements:
  * **SET**: Assign a value to a variable.
    - ```
       SET <variable> = <value>
      ```
  * **SELECT**: Select a graph described by a pattern from a service, given various constraints. Graph patterns are expressed using concepts from the [biolink-model](https://biolink.github.io/biolink-model/).
    - ```
       SELECT <graph>
       FROM <service>
       [WHERE <constraint> [AND <constraint]*]
       [[SET <jsonpath> AS <var> | [SET <var>]]*```
  * **CREATE GRAPH**: Create a graph at a service.
    - ```
       CREATE GRAPH <var> AT <service> AS <name>
      ```

## Translator Standard API

The [Translator standard graph API](https://github.com/NCATS-Gamma/NCATS-ReasonerStdAPI) is a protocol for exchanging graphs with federated data sources. TranQL works with endpoints supporting this standard.

## Backplane

The TranQL Backplane is a collection of endpoints supporting the standard API which implement reusable question answering services, or modules.

Backplane modules support a simplified syntax in the language for greater readability.
