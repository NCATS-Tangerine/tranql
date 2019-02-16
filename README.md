# TranQL

TranQL is a query language for interactive exploration of federated graph oriented data sources.

## Background

Previous [work](https://github.com/NCATS-Tangerine/ros) focused on a workflow language for automating queries. We've also prototyped similar workflows using the Common Workflow Language (CWL).

Workflow languages generally provide capabilities to support large scale, fault tolerant, reproducible, automated computing. These are critical features where processes that have been refined by teams over time must be automated and shared. Common characteristics of these systems include:
  * The ability to **manage multiple interacting, long running** third party programs (eg, genomic sequence alignment)
  * Infrastructure level support for **reproducability** via artifacts like Docker containers.
  * **Complex syntax** in formats like YAML, generally unfamilar to SMEs in clinical / medical specialties.

While these features are essential for some applications, they are neither targeted at nor well suited to
  * **Iterative, interactive exploration** of large data sets.
  * **Accessibility** to communities like clinical data specialists and medical experts.
  * **A programmatic interface between applications** and a data source.
  
## Interactive Exploration

The ability to explore large data sets with queries is extremely familiar to clinical data experts and many medical informatics specialists. To make semantic databases more accessible to these communities, we designed TranQL - a query language with structural and syntactic similarities to familiar languages that is able to interact with distributed graphs.

The [Structured Query Language (SQL)](https://en.wikipedia.org/wiki/SQL) is among the most pervasive data query languages in use. It is vital to the work of clinical data specialists. TranQL borrows concepts from SQL while adding graph semantics.

## Design Overview

TranQL is designed as a traditional parser which produces an abstract syntax tree modeling the program's constructs which are executed sequentially. It supports three statement types:
  * **SET** Syntax: `SET <variable> = <value>`
  * **SELECT** Syntax: `SELECT <graph> FROM <service> [WHERE <constraint> [AND <constraint]*] [[SET <jsonpath> AS <variable>\ | [SET <var>]]*
  * **CREATE GRAPH** Syntax: `CREATE GRAPH <var> AT <service> AS <name>`
  
## Example

```
--
-- Workflow 5
--
--   Modules 1-4: Chemical Exposures by Clinical Clusters
--      For ICEES cohorts, eg, defined by differential population
--      density, which chemicals are associated with these
--      cohorts with a p_value lower than some threshold?
--
--   Modules 5-*: Knowledge Graph Phenotypic Associations 
--      For chemicals produced by steps 1-4, what phenotypes are
--      associated with exposure to these chemicals?
--

SELECT disease->chemical_substance
  FROM '/clinical/cohort/disease_to_chemical_exposure'
 WHERE disease = 'asthma'
   AND EstResidentialDensity < '2'
   AND cohort = 'all_patients'
   AND max_p_value = '0.5'
   SET '$.knowledge_graph.nodes.[*].id' AS chemical_exposures

SELECT chemical_substance->gene->biological_process->phenotypic_feature
  FROM '/graph/gamma/quick'
 WHERE chemical_substance = $chemical_exposures
   SET phenotypic_pathways 

CREATE GRAPH $phenotypic_pathways
    AT '/visualize/ndex'
    AS 'wf5_pheno_paths'

CREATE GRAPH $phenotypic_pathways
    AT '/visualize/gamma'
    AS 'wf5_pheno_paths'
```
