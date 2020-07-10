---
layout: default
title: TranQL Jupyter
nav_order: 4
repo: https://github.com/frostyfan109/tranql-jupyter
---
# About
[TranQL-Jupyter]({{ page.repo }}) is a package which introduces TranQL bindings to Jupyter. Its primary purposes are:
1. Making TranQL queries using the `%tranql_query` magic
2. Adding utilities for working with and visualizing knowledge graphs

# Installation
Just like TranQL, TranQL-Jupyter is also designed to be used within a Python 3.7.x virtual environment.
```
git clone {{ page.repo }}
pip install ./tranql-jupyter
# Or
cd tranql-jupyter
python setup.py install
```
You also need to install the TranQL Interpreter. It is recommended to install it via its setup.py to cut down on installation time,
although it can also be installed with pip:
```
git clone <tranql repository>
cd tranql
python setup.py install
# Alternatively (not recommended)
pip install ./tranql
```

# Usage

## Quick start
```
In [1]: %load_ext tranql_jupyter
        kg_1 = %tranql_query SELECT chemical_substance->gene from "/graph/gamma/quick" where chemical_substance="CHEBI:30769"
        kg_2 = %tranql_query SELECT chemical_substance->gene from "/graph/gamma/quick" where chemical_substance="CHEBI:27732"

        union = kg_1 + kg_2
        union.render_force_graph_2d()
```

## Full Reference
See [here]({{ page.repo }}/blob/master/README.md#usage) for a complete reference.

## Full Example Notebook
For a comprehensive example of the usage of TranQL-Jupyter, see [this notebook](https://nbviewer.jupyter.org/github/frostyfan109/TranQL-Jupyter/blob/master/test_notebooks/Demo%20Notebook.ipynb).
