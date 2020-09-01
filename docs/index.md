---
layout: default
title: Overview
nav_order: 1
robokop: https://researchsoftwareinstitute.github.io/data-translator/apps/robokop/
icees: https://researchsoftwareinstitute.github.io/data-translator/apps/icees/
---
# Overview

[**TranQL**](http://tranql.renci.org/) (Translator Query Language) is an interactive environment for the iterative exploration of federated knowledge graphs with semantically rich visualizations. It queries knowledge models from multiple Translator reasoners federeated into unified schemas. The user interface supports iteratively querying, caching, visualizing, modifying, and requerying data across the federation. Completed queries can be incorporated into software systems requiring parameterized automation of the Translator semantic network.

TranQL was developed by [RENCI](https://renci.org/) to automate graph-oriented queries over Translator Knowledge Graph Standard (KGS) API services. The KGS API is the interface presented by [ROBOKOP]({{ page.robokop }}), [ICEES]({{ page.icees }}), and other Translator “Reasoners”. TranQL offers a  query and visualization interface to federated knowledge networks, with syntax that blends elements of relational and graph semantics to express a graph query and enable joins across Translator Reasoners. A simple, interactive user interface accepts a query in the TranQL query language, executes the query across one or more Reasoners, and visualizes the resulting KG.

An example of a TranQL query and resultant KG is shown below. Here, TranQL was used to join results from [ICEES]({{ page.icees }}) and [ROBOKOP]({{ page.robokop }}) and explore relationships between patients with asthma who are vs are not responsive to treatment (as defined by emergency department or inpatient visits for respiratory issues), their chemical exposures, and the downstream gene targets, biological processes, and phenotypic features associated with those exposures.

The query asks: for patients in [ICEES]({{ page.icees }}) with asthma-like conditions who are vs are not responsive to treatment (as defined by ED/inpatient visits for respiratory issues), what are their chemical exposures and what are the gene targets, biological processes, and phenotypic features associated with those chemical exposures. Note that the first part the workflow invokes [ICEES]({{ page.icees }}) and the second part invokes [ROBOKOP]({{ page.robokop }}).

![Screenshot depicting interactive graph visualization]({{ site.baseurl }}/assets/images/tranql-interactive-output.png)

TranQL is not specific to [ICEES]({{ page.icees }}) and [ROBOKOP]({{ page.robokop }}). Rather can serve as a bridge across Translator Reasoners to provide workflow automation and interactive visualization of output.

As a new tool, TranQL is now being implemented and evaluated in driving use cases such as the one described above. However, we expect this tool to have broad applicability across the Translator program, including application across other open Translator Clinical Knowledge Sources (e.g., [Columbia Open Health Data](http://smart-api.info/ui/9fbeaeabd19b334fa0f1932aa111bf35), [Clinical Profiles](https://model.clinicalprofiles.org/clinicalprofile.html)).
