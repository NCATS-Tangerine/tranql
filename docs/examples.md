---
layout: default
title: Examples
nav_order: 4
---
# Examples

## Basic query
What chemical substances are connected to genes which are connected to asthma?
In this example, only Robokop is being queried.
```
select chemical_substance->gene->disease
  from "/graph/gamma/quick"
 where disease="asthma"
```

## Using predicates
For large queries of thousands of nodes and edges, predicates can be used
to cut down on the fluff in the results and get directly what you're looking for.
In this example, we take the previous query but specify the exact relationships
we're looking for between the node types.
```
select chemical_substance-[decreases_activity_of]->gene-[contributes_to]->disease
  from "/graph/gamma/quick"
 where disease="asthma"
```

Note: in the previous two queries, an explicit curie for "asthma" is not specified; instead, we are relying on the interpreter to resolve asthma into
an identifier for us. This practice is no longer recommended, and the setting "dynamic id resolution" has to be explicitly enabled within the web app
in order for it to work. It is strongly recommended to use an ontological identifier instead.

## Set statements
If used multiple times throughout a query, or just for clarity, set statements can be used to create variables within a TranQL query.
To then refer to the variable, it should be prefixed with a "$". In this query, a set statement is used to create
the variable "target_gene", which is then referred to in the where statement. The query selects chemical substances/drugs
that target $target_gene (MAPK1).
```
set target_gene = 'HGNC:6871' --mapk1
select chemical_substance->gene
  from '/graph/gamma/quick'
 where gene = $target_gene
```

## Complex query & backwards arrows
This query involves a lot of steps. The disease curie is asthma. If you look closely, you'll notice
that the final edge is actually phenotypic_feature<-disease. Backwards arrows can be very useful
when multiple things are trying to be accomplished in a single query, such as in this one.
```
set drug = 'PUBCHEM:2083'
set disease = 'MONDO:0004979'

select chemical_substance->gene->anatomical_entity->phenotypic_feature<-disease
  from '/graph/gamma/quick'
 where chemical_substance = $drug
   and disease = $disease
```

## Functions
Within a where clause, one of various functions can be used in place of an exact value. Most of these are ontological functions
offered by the [ONTO API](http://onto.renci.org). The whole list can be found in [udfs.yaml](https://github.com/frostyfan109/tranql/blob/master/tranql/udfs.yaml)
and the source is located in [udfs.py](https://github.com/frostyfan109/tranql/blob/master/tranql/udfs.py). Some useful functions to be aware of are:
- `descendants(curie)`
- `children(curie)`
- `parents(curie)`

The following query demonstrates how to use a function. Some function's arguments may vary, but most will just take a curie.
```
select chemical_substance->gene->disease
  from "/graph/gamma/quick"
 where disease=children("MONDO:0004979")
```
In this query, we select chemical_substance->gene->disease, where disease is the children of asthma (MONDO:0004979).

If we perform a query to the ONTO service ourselves:
```
curl -X GET "https://onto.renci.org/children/MONDO%3A0004979" -H "accept: application/json"
```
we can find out that `children("MONDO:0004979")` actually resolves to:
```
["MONDO:0001491","MONDO:0004765","MONDO:0004766","MONDO:0004784","MONDO:0005405","MONDO:0022742"]
```
These curies are all variants of asthma. For example, the first curie, "MONDO:0001491" is "cough variant asthma".
