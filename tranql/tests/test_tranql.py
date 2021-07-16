import os
import requests
import yaml
from functools import reduce
from tranql.main import TranQL
from tranql.tranql_ast import SetStatement, SelectStatement, custom_functions
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.utils.merge_utils import connect_knowledge_maps, find_all_paths
from tranql.tests.mocks import MockHelper
from tranql.tests.mocks import MockMap
from tranql.tranql_schema import SchemaFactory
import requests_mock
from unittest.mock import patch
import copy, time
from tranql.tests.mock_graph_adapter import GraphInterfaceMock
#set_verbose ()

def assert_parse_tree (code, expected):
    """ Parse a block of code into a parse tree. Then assert the equality
    of that parse tree to a list of expected tokens. """
    tranql = TranQL ()
    tranql.resolve_names = False
    actual = tranql.parser.parse (code).parse_tree
    #print (f"{actual}")
    assert_lists_equal (
        actual,
        expected)

#####################################################
#
# Parser tests. Verify we produce the AST for the
# expected grammar correctly.
#
#####################################################

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_predicate (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "predicates")

    """ Test parsing a predicate. """
    print (f"test_parse_predicate()")
    assert_parse_tree (
        code = """
        SELECT chemical_substance-[treats]->disease
          FROM "/graph/gamma/quick"
          WHERE chemical_substance='PUBCHEM:2083'
            SET "$.knowledge_graph.nodes.[*].id as indications
        """,
        expected = [
            [ [ "select",
                "chemical_substance",
                [ "-[",
                  "treats",
                  "]->"
                ], "disease", "\n"
            ],
            "          ",
            [ "from", [ "/graph/gamma/quick"] ],
            ["where",
             [
                 "chemical_substance",
                 "=",
                 "PUBCHEM:2083"
             ]
            ], [ "" ]
            ]])

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_function (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing and resolving function values (including nested) """
    # Create a custom function that concats two strings
    @custom_functions.custom_function
    def concat_strings(str_a, str_b):
        return str_a + str_b

    # Create a function that returns "asth"
    @custom_functions.custom_function
    def get_asthma():
        return "asth"

    # Test concat function
    code = """
        SELECT chemical_substance->gene->disease
          FROM "/graph/gamma/quick"
         WHERE disease=concat_strings(get_asthma(), "ma")
    """
    expected_where = [
        [
            "disease",
            "=",
            "asthma"
        ]
    ]
    tranql = TranQL ()
    tranql.resolve_names = False
    result_where = tranql.parse(code).statements[0].where

    assert_lists_equal(
        result_where,
        expected_where
    )

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_list_function (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test resolving a function that returns a list """
    # Create a function that returns a list
    @custom_functions.custom_function
    def returns_list():
        return ["asthma", "smallpox"]

    # Test list function
    code = """
        SELECT chemical_substance->gene->disease
          FROM "/graph/gamma/quick"
         WHERE disease=returns_list()
    """
    expected_where = [
        [
            "disease",
            "=",
            [
                "asthma",
                "smallpox"
            ]
        ]
    ]
    tranql = TranQL ()
    tranql.resolve_names = False
    result_where = tranql.parse(code).statements[0].where

    assert_lists_equal(
        result_where,
        expected_where
    )

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_kwarg_function (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing of a function with keyword arguments """
    # Create a function that returns a list
    @custom_functions.custom_function
    def kwarg_function(str_a, str_b, prefix="_PREFIX_", suffix="_SUFFIX_"):
        return prefix + str_a + str_b + suffix

    # Test list function
    code = """
        SELECT chemical_substance->gene->disease
          FROM "/graph/gamma/quick"
         WHERE disease=kwarg_function("beginning of body", "ending of body", prefix="_CUSTOM_PREFIX_")
    """
    expected_where = [
        [
            "disease",
            "=",
            "_CUSTOM_PREFIX_beginning of bodyending of body_SUFFIX_"
        ]
    ]
    tranql = TranQL ()
    tranql.resolve_names = False
    result_where = tranql.parse(code).statements[0].where

    assert_lists_equal(
        result_where,
        expected_where
    )

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_list (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing of lists within where statements """
    """ Also make sure that vars are properly recognized """
    code = """
        SELECT chemical_substance->gene->disease
          FROM "/graph/gamma/quick"
         WHERE disease = ['asthma', 'smallpox', $my_var]
    """
    expected_where = [
        [
            "disease",
            "=",
            [
                "asthma",
                "smallpox",
                "$my_var"
            ]
        ]
    ]
    tranql = TranQL ()
    tranql.resolve_names = False
    result_where = tranql.parse(code).statements[0].where

    assert_lists_equal(
        result_where,
        expected_where
    )


@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_set (GraphIntefaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing set statements. """
    print (f"test_parse_set()")
    assert_parse_tree (
        code = """
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/' """,
        expected = [
            ["set", "disease", "=", "asthma"],
            ["set", "max_p_value", "=", "0.5"],
            ["set", "cohort", "=", "COHORT:22"],
            ["set", "population_density", "=", 2],
            ["set", "icees.population_density_cluster", "=", "http://localhost/ICEESQuery"],
            ["set", "gamma.quick", "=", "http://robokop.renci.org:80/api/simple/quick/"]
        ])

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_set_with_comment (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test parsing set statements with comments. """
    print (f"test_parse_set_with_comment()")
    assert_parse_tree (
        code = """
        -- This is a comment
        SET disease = 'asthma' """,
        expected = [
            ["set", "disease", "=", "asthma"]
        ])

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_select_simple (GraphIntefaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the token stream of a simple select statement. """
    print (f"test_parse_select_simple()")
    assert_parse_tree (
        code = """
        SELECT chemical_substance->gene->biological_process->phenotypic_feature
          FROM "/graph/gamma/quick"
         WHERE chemical_substance = $chemical_exposures
           SET knowledge_graph """,
        expected = [
            [["select", "chemical_substance", "->", "gene", "->", "biological_process", "->", "phenotypic_feature", "\n"],
             "          ",
             ["from", ["/graph/gamma/quick"]],
             ["where", ["chemical_substance", "=", "$chemical_exposures"]],
             ["set", ["knowledge_graph"]]]
        ])

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_select_complex (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the token stream of a more complex select statement. """
    print (f"test_parse_select_complex()")
    assert_parse_tree (
        code = """
        SELECT disease->chemical_substance
          FROM "/flow/5/mod_1_4/icees/by_residential_density"
         WHERE disease = "asthma"
           AND EstResidentialDensity < "2"
           AND cohort = "COHORT:22"
           AND max_p_value = "0.5"
           SET '$.nodes.[*].id' AS chemical_exposures """,
        expected = [
            [["select", "disease", "->", "chemical_substance", "\n"],
             "          ",
             ["from", ["/flow/5/mod_1_4/icees/by_residential_density"]],
             ["where",
              ["disease", "=", "asthma"], "and",
              ["EstResidentialDensity", "<", "2"], "and",
              ["cohort", "=", "COHORT:22"], "and",
              ["max_p_value", "=", "0.5"]
             ],
             ["set", ["$.nodes.[*].id", "as", "chemical_exposures"]]]
        ])

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_parse_query_with_repeated_concept (GraphInterfaceMock, requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the parser accepts a grammar allowing concept names to be prefixed by a name
    and a colon. """
    print (f"test_parse_query_with_repeated_concept")
    assert_parse_tree (
        code="""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'asthma'
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
        """,
        expected = [
            [["select", "cohort_diagnosis:disease","->","diagnoses:disease","\n"],
             "  ",
             ["from",
              ["/clinical/cohort/disease_to_chemical_exposure"]
             ],
             ["where",
              ["cohort_diagnosis","=","asthma"],
              "and",
              ["Sex","=","0"],
              "and",
              ["cohort","=","all_patients"],
              "and",
              ["max_p_value","=","0.5"]
             ],
             ["set",
              ["$.knowledge_graph.nodes.[*].id","as","diagnoses"]
             ]
            ]])

#####################################################
#
# AST tests. Test abstract syntax tree components.
#
#####################################################
def test_ast_set_variable (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test setting a varaible to an explicit value. """
    print ("test_ast_set_variable ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value="x")
    statement.execute (tranql)
    assert tranql.context.resolve_arg ("$variable") == 'x'

def test_ast_set_variable_as_list ():
    tranql = TranQL()
    curie_list = ['chebi:16576', 'chebi:00004']
    ast_tree = tranql.parse(f"""
        set chemical_substance = {curie_list}
        """)
    set_statment_parsed = ast_tree.parse_tree[0]
    set_statment = ast_tree.statements[0]
    value_list = set_statment_parsed[3]
    assert isinstance(value_list, list)
    assert value_list[0] == curie_list[0] and value_list[-1] == curie_list[-1]
    set_statment.execute(tranql)
    assert tranql.context.mem.get('chemical_substance') == curie_list


def test_ast_set_graph (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Set a variable to a graph passed as a result. """
    print ("test_ast_set_graph ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value=None, jsonpath_query=None)
    statement.execute (tranql, context={ 'result' : { "a" : 1 } })
    assert tranql.context.resolve_arg ("$variable")['a'] == 1
def test_ast_set_graph (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Set a variable to the value returned by executing a JSONPath query. """
    print ("test_ast_set_graph ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value=None, jsonpath_query="$.nodes.[*]")
    statement.execute (tranql, context={
        'result' : {
            "nodes" : [ {
                "id" : "x:y"
            } ]
        }
    })
    assert tranql.context.resolve_arg ("$variable")[0]['id'] == "x:y"
def test_ast_generate_questions (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
           -- named query concepts work.
           -- the question graph is build incorporating where clause constraints.
    """
    print ("test_ast_set_generate_questions ()")
    app = TranQL ()
    app.resolve_names = False
    ast = app.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)
    question = ast.statements[0].generate_questions (app)['message']
    assert question['query_graph']['nodes']['cohort_diagnosis']['id'] == ['MONDO:0004979']
    assert question['query_graph']['nodes']['cohort_diagnosis']['category'] == 'biolink:Disease'
    assert question['query_graph']['nodes']['diagnoses']['category'] == 'biolink:Disease'


def test_ast_generate_questions_from_list():
    tranql = TranQL()
    tranql.dynamic_id_resolution = True
    curie_list = ['chebi:123', 'CHEBI:234']
    ast = tranql.parse(
        f"""
            SET c = {curie_list}
            SELECT chemical_substance->gene
            FROM '/schema'
            WHERE chemical_substance=$c
            """
    )
    # first let's run the set statement
    ast.statements[0].execute(tranql)
    questions = ast.statements[1].generate_questions(tranql)['message']
    chemical_node =  questions['query_graph']['nodes']['chemical_substance']
    assert chemical_node['id'] == curie_list
    assert chemical_node['category'] == 'biolink:ChemicalSubstance'
    assert questions['query_graph']['nodes']['gene']['category'] == 'biolink:Gene'

    # Multiple variable setting
    chemicals = curie_list
    gene_list = ['GENE:1', 'GENE:2']
    ast_2 = tranql.parse(
        f"""
        SET chemicals= {chemicals}
        SET genes = {gene_list}
        SELECT chemical_substance->gene
        FROM '/schema'
        WHERE gene=$genes
        AND chemical_substance=$chemicals
        """
    )
    # Here we should get the following  chebi:123 -> BRAC1, chebi:123 -> BRAC2 , water -> BRAC1 and water -> BRAC2
    # run set statements
    set_chemicals = ast_2.statements[0]
    set_genes = ast_2.statements[1]
    select_statement = ast_2.statements[2]

    set_chemicals.execute(tranql)
    set_genes.execute(tranql)

    # generate question

    questions = select_statement.generate_questions(tranql)['message']
    # get all chemical and genes

    nodes = questions['query_graph']['nodes']
    chemical_node = nodes['chemical_substance']
    gene_node = nodes['gene']
    chemicals_ids = chemical_node['id']
    gene_ids = gene_node['id']
    chemicals.sort()
    chemicals_ids.sort()
    gene_ids.sort()
    gene_list.sort()
    assert_lists_equal(chemicals_ids, chemicals)
    assert_lists_equal(gene_list, gene_ids)

def test_ast_generate_questions_list_variable():
    # make sure that a list is parsed correctly when it contains variables

    """ currently this test doesn't pass due to a bug in expand_nodes. the interpreter
    will only call expand_nodes on the first node concept. so, if a variable is not
    the first element in a list, it won't be resolved. if a variable is the first element
    in a list, the entire list will be set to just that variable.

    ex: set $var = "HGNC:X"
        where gene=[$var, "HGNC:Y", "HGNC:Z"]
    becomes:
        ["HGNC:X"]
    should be:
        ["HGNC:X", "HGNC:Y", "HGNC:Z"]

    ex2: set $var = "HGNC:X"
         where gene=["HGNC:Y", $var, "HGNC:Z"]
    becomes:
         ["HGNC:Y", "$var", "HGNC:Z"]
    should be:
         ["HGNC:Y", "HGNC:X", "HGNC:Z"]
    """


    tranql = TranQL()
    ast_3 = tranql.parse(f"""
        SET var_str = 'CHEBI:0'
        SET var_list = ['CHEBI:22', 'CHEBI:33']
        SELECT chemical_substance->gene->disease
          FROM "/graph/gamma/quick"
         WHERE chemical_substance = [$var_str, 'CHEBI:1', $var_list]
    """)
    set_var_str = ast_3.statements[0]
    set_var_list = ast_3.statements[1]
    select_statement = ast_3.statements[2]

    set_var_str.execute (tranql)
    set_var_list.execute (tranql)
    question = select_statement.generate_questions (tranql)['message']
    chem_ids = question['query_graph']['nodes']['chemical_substance']['id']
    assert_lists_equal(sorted(chem_ids), sorted(['CHEBI:0', 'CHEBI:22', 'CHEBI:33', 'CHEBI:1']))

def test_generate_questions_where_clause_list():
    # Try to generate questions if values for nodes are set as lists in the where clause
    curies = ['HGNC:3', 'HGNC:34']
    query = f"""
    SELECT gene->chemical_substance
    FROM '/schema'
    WHERE gene={curies}
    """
    tranql = TranQL()
    ast = tranql.parse(query)
    select_statememt = ast.statements[0]
    question = select_statememt.generate_questions(tranql)['message']
    gene_curies = question['query_graph']['nodes']['gene']['id']
    # we should have two questions
    assert set(gene_curies) == set(curies)

def test_ast_format_constraints (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- The syntax to pass values to reasoners in the where clause (e.g. "icees.foo = bar") functions properly
    """
    print("test_ast_format_constraints ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    ast = tranql.parse ("""
        SELECT population_of_individual_organisms->chemical_substance
          FROM "/clinical/cohort/disease_to_chemical_exposure?provider=icees"
         WHERE icees.should_format = 1
           AND robokop.should_not_format = 0
    """)
    select = ast.statements[0]
    select.format_constraints(tranql)
    print(select.where)
    assert_lists_equal(select.where, [
        ['should_format', '=', 1],
        ['should_format', '=', 1],
        ['robokop.should_not_format', '=', 0],
        ['robokop.should_not_format', '=', 0]
    ])
def test_ast_backwards_arrow (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print("test_ast_backwards_arrow ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    ast = tranql.parse ("""
        SELECT gene->biological_process<-microRNA
          FROM "/schema"
    """)
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))
    backwards_question = statements[1].generate_questions(tranql)["message"]

    edge_keys = list(backwards_question["query_graph"]["edges"].keys())
    assert len(edge_keys) == 1
    assert backwards_question["query_graph"]["edges"][edge_keys[0]]["subject"] == "microRNA"
    assert backwards_question["query_graph"]["edges"][edge_keys[0]]["object"] == "biological_process"
def test_ast_decorate_element (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- The SelectStatement::decorate method properly decorates both nodes and edges
    """
    print("test_ast_decorate_element ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    ast = tranql.parse ("""
        SELECT chemical_substance->disease
          FROM "/graph/gamma/quick"
    """)
    select = ast.statements[0]
    node = {
        "id": "CHEBI:36314",
        "name": "glycerophosphoethanolamine",
        "omnicorp_article_count": 288,
        "type": "chemical_substance"
    }
    edge = {
        "ctime": [
            1544077522.7678425
        ],
        "edge_source": [
            "chembio.graph_pubchem_to_ncbigene"
        ],
        "id": "df662e2842d44fa2c0b5d945044317e3",
        "predicate_id": "SIO:000203",
        "publications": [
            "PMID:16217747"
        ],
        "relation": [
            "CTD:interacts_with"
        ],
        "relation_label": [
            "interacts"
        ],
        "source_id": "CHEBI:36314",
        "target_id": "HGNC:8971",
        "type": "directly_interacts_with",
        "weight": 0.4071474314830641
    }
    select.decorate(node,True,{
        "schema" : select.get_schema_name(tranql)
    })
    select.decorate(edge,False,{
        "schema" : select.get_schema_name(tranql)
    })
    has_reasoner_attr = False
    for attribute in  node['attributes']:
        if attribute['name'] == 'reasoner':
            assert 'robokop' in attribute['value']
            has_reasoner_attr = True
            break

    assert has_reasoner_attr
    has_reasoner_attr = False

    for attribute in edge['attributes']:
        if attribute['name'] == 'reasoner':
            assert 'robokop' in attribute['value']
            has_reasoner_attr = True
            break
    assert has_reasoner_attr
    # assert_lists_equal(edge["source_database"],["unknown"])
def test_ast_resolve_name (requests_mock):
    set_mock(requests_mock, "resolve_name")
    """ Validate that
            -- The SelectStatement::resolve_name method will correctly retrieve equivalent identifiers from a given name
    """
    print("test_ast_resolve_name ()")
    assert_lists_equal(SelectStatement.resolve_name("ibuprofen","chemical_substance"),[
        'CHEBI:132922',
        'CHEBI:5855',
        'CHEBI:43415',
        'PUBCHEM:3672',
        'MESH:D007052',
        'CHEBI:5855',
        'CHEMBL:CHEMBL521']
    )
def test_ast_predicate_question (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- A query with a predicate will be properly formatted into a question graph
    """
    print("test_ast_predicates ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT chemical_substance-[treats]->disease
          FROM "/graph/gamma/quick"
         WHERE chemical_substance='CHEMBL:CHEMBL521'
    """)
    select = ast.statements[0]
    question = select.generate_questions(tranql)["message"]["query_graph"]

    assert len(question["edges"]) == 1
    edge_keys = list(question['edges'].keys())
    assert question["edges"][edge_keys[0]]["predicate"] == "biolink:treats"
def test_ast_multiple_reasoners (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- A query spanning multiple reasoners will query multiple reasoners.
            -- A transitions that multiple reasoners support will query each reasoner that supports it.
    """
    print("test_ast_multiple_reasoners ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    ast = tranql.parse ("""
        SELECT chemical_substance->disease->gene
          FROM "/schema"
    """)
    # RTX and Robokop both support transitions between chemical_substance->disease and only Robokop supports transitions between disease->gene
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))
    assert_lists_equal(statements[0].query.order,['chemical_substance','disease'])
    assert statements[0].get_schema_name(tranql) == "robokop"

    assert_lists_equal(statements[1].query.order,['chemical_substance','disease'])
    assert statements[1].get_schema_name(tranql) == "rtx"

    assert_lists_equal(statements[2].query.order,['disease','gene'])
    assert statements[2].get_schema_name(tranql) == "robokop"


@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_ast_merge_knowledge_maps (GraphInterfaceMock, requests_mock):
    responses = [
        {
            "message":
                {
                    "knowledge_graph": {
                        "edges": {},
                        "nodes": {}
                    },
                    'results': [
                        {
                            'node_bindings': {
                                'chemical_substance': [{"id": "CHEBI:100"}],
                                'disease': [{"id": 'MONDO:50'}]
                            },
                            'edge_bindings': {
                                'e0': [{
                                    "id": 'ROOT_EDGE'
                                }]
                            }
                        }
                    ],
                    'query_graph': {
                        'nodes': {
                            "chemical_substance": {'category': 'chemical_substance'},
                            "disease": {'category': 'disease'}
                        },
                        'edges': {
                            'e0': {'subject': 'chemical_substance', 'object': 'disease'}
                        }
                    }
                }
        },
        {
            "message": {
                "knowledge_graph": {
                    "edges": {},
                    "nodes": {}
                },
                'results': [
                    {
                        'node_bindings': {
                            'disease': [{"id": 'MONDO:50'}],
                            'gene': [{"id": 'HGNC:1'}],
                            'metabolite': [{"id": 'KEGG:C00017'}]
                        },
                        'edge_bindings': {
                            'e1': [{"id": 'TEST_EDGE'}]
                        }
                    }
                ],
                'query_graph': {
                    'nodes': {
                        'disease': {'category': 'disease'},
                        "gene": {'category': 'gene'},
                        "metabolite": {'category': 'metabolite'}
                    },
                    'edges': {
                        'e0': {'subject': 'disease', 'object': 'gene'},
                        'e1': {'subject': 'gene', 'object': 'metabolite'}
                    }
                }
            }
        },
        {
            "message": {
                "knowledge_graph": {
                    "edges": {},
                    "nodes": {}
                },
                'results': [
                    {
                        'node_bindings': {
                            'disease': [{"id": 'MONDO:50'}],
                            'gene': [{"id": 'HGNC:1'}],
                            'metabolite': [{"id": 'KEGG:FOOBAR'}]
                        },
                        'edge_bindings': {

                        }
                    }
                ],
                'query_graph': {
                    'nodes': {
                        "disease": {'category': 'disease'},
                        "gene": {'category': 'gene'},
                        "metabolite": {'category': 'metabolite'}
                    },
                    'edges': {
                        "e0": {'subject': 'disease', 'object': 'gene'},
                        "e1": {'subject': 'gene', 'object': 'metabolite'}
                    }
                }
            }
        },
        {
            "message": {
                "knowledge_graph": {
                    "edges": {},
                    "nodes": {}
                },
                'results': [
                    {
                        'node_bindings': {
                            'metabolite': [{"id": 'KEGG:FOOBAR'}],
                            'protein': [{"id": 'UniProtKB:TESTING'}]
                        },
                        'edge_bindings': {
                        }
                    }
                ],
                'query_graph': {
                    'nodes': {
                        "metabolite": {'category': 'metabolite'},
                        "protein": {'category': 'protein'}
                    },
                    'edges': {
                        'e0': {'subject': 'metabolite', 'object': 'protein'}
                    }
                }
            }
        },
        {
            "message": {
                "knowledge_graph": {
                    "edges": {},
                    "nodes": {}
                },
                'results': [
                    {
                        'node_bindings': {
                            'metabolite': [{"id": 'KEGG:C00017'}],
                            'protein': [{"id": 'UniProtKB:Q9NZJ5'}]
                        },
                        'edge_bindings': {

                        }
                    }
                ],
                'query_graph': {
                    'nodes': {
                        'metabolite': {'category': 'metabolite'},
                        'protein': {'category': 'protein'}
                    },
                    'edges': {
                        'e0': {'subject': 'metabolite', 'object': 'protein'}
                    }
                }
            }
        }
    ]

    merged = connect_knowledge_maps([r["message"] for r in responses])
    ###
    # The Knowledge map is only valid if it has a connection, note that it is a filler
    # for the blanks of the question graph.
    # If a knowledge map with no edge_bindings is returned then it's not very useful as
    # it doesn't tell the connection that the nodes bound have.
    # so to be merged properly it should atleast have an edge binding
    # above responses look like the following paths
    # Response 1: chemical_substance(CHEBI:100)-[e0:ROOTEDGE]-disease(MONDO:50)
    # Response 2: disease (MONDO:50)   gene(HGNC:1)-[e1: TESTEDGE]-chemical(KEGG:C00017)
    # Response 3: disease (MONDO:50)  gene(HGNC:1)   metabolite(KEGG:FOOBAR)
    # Reponse 4: metabolite(KEGG:FOOBAR) protein(UniPRotKB:TESTING)
    # Response 5: metabolite(KEGG:C00017) protein(UniprotKb:Q9NZJ5)
    # not that Response 3, 4 and 5 are just nodes so we can drop them
    # the paths to expect here are
    # response 1's full path
    # response 2's connected path
    ###
    assert_lists_equal(ordered(merged), ordered([
        {
            "node_bindings" : {
                "chemical_substance" : [{"id":"CHEBI:100"}],
                "disease" : [{"id":"MONDO:50"}],
            },
            "edge_bindings" : {
                "e0" : [{"id":"ROOT_EDGE"}]
            },
            "score": 0
        },
        {
            "node_bindings" : {
                "gene" : [{"id": "HGNC:1"}],
                "metabolite" : [{"id": "KEGG:C00017"}]
            },
            "edge_bindings" : {
                "e1" : [{"id": "TEST_EDGE"}],
            },
            "score": 0
        }
    ]))


def test_ast_plan_strategy (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print ("test_ast_plan_strategy ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    tranql.resolve_names = False
    # QueryPlanStrategy always uses /schema regardless of the `FROM` clause.
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/schema'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)

    select = ast.statements[0]
    plan = select.planner.plan (select.query)

    # Assert that it has planned to query both gamma and rtx
    assert (
        (plan[0][1] == "/graph/gamma/quick" and plan[1][1] == "/graph/rtx") or
        (plan[1][1] == "/graph/rtx" and plan[1][1] == "/graph/gamma/quick")
    )
    # Both should be querying the same thing (disease->diseasee), differing only in the sub_schema that they are querying
    for sub_schema_plan in plan:
        assert sub_schema_plan[2][0][0].type_name == "biolink:Disease"
        assert sub_schema_plan[2][0][0].name == "cohort_diagnosis"
        assert sub_schema_plan[2][0][0].curies == ["MONDO:0004979"]

        assert sub_schema_plan[2][0][1].direction == "->"
        assert sub_schema_plan[2][0][1].predicate == None

        assert sub_schema_plan[2][0][2].type_name == "biolink:Disease"
        assert sub_schema_plan[2][0][2].name == "diagnoses"
        assert sub_schema_plan[2][0][2].curies == []
def test_ast_implicit_conversion (requests_mock):
    set_mock(requests_mock, "workflow-5")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    ast = tranql.parse ("""
        SELECT drug_exposure->chemical_substance
         FROM '/schema'
    """)
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))

    assert_lists_equal(statements[0].query.order,["drug_exposure","chemical_substance"])
    assert statements[0].get_schema_name(tranql) == "implicit_conversion"

def test_ast_plan_statements (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print("test_ast_plan_statements ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    tranql.resolve_names = False
    # QueryPlanStrategy always uses /schema regardless of the `FROM` clause.
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/schema'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)


    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))

    assert len(statements) == 2 # roger is not accessed via schema
    for statement in statements:
        assert_lists_equal(
            list(statement.query.concepts.keys()),
            [
                "cohort_diagnosis",
                "diagnoses"
            ]
        )

        assert statement.query.concepts['cohort_diagnosis'].curies == ["MONDO:0004979"]
        assert statement.query.concepts['diagnoses'].curies == []
        # TODO: figure out why there are duplicates generated??
        assert_lists_equal(statement.where, [
            ['cohort_diagnosis', '=', 'MONDO:0004979'],
            ['Sex', '=', '0'], ['Sex', '=', '0'],
            ['cohort', '=', 'all_patients'],
            ['cohort', '=', 'all_patients'],
            ['max_p_value', '=', '0.5'],
            ['max_p_value', '=', '0.5']
        ])
        assert statement.set_statements == []

    assert (
        (statements[0].service == "/graph/gamma/quick" and statements[1].service == "/graph/rtx") or
        (statements[0].service == "/graph/rtx" and statements[1].service == "/graph/gamma/quick")
    )

def test_ast_bidirectional_query (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that we parse and generate queries correctly for bidirectional queries. """
    print ("test_ast_bidirectional_query ()")
    app = TranQL (options={
        'recreate_schema': True
    })
    app.resolve_names = False
    disease_id = "MONDO:0004979"
    chemical = "PUBCHEM:2083"
    app.context.set ("drug", chemical)
    app.context.set ("disease", disease_id)
    mocker = MockHelper ()
    expectations = {
        "cop.tranql" : mocker.get_obj ("bidirectional_question.json")
    }
    queries = { os.path.join (os.path.dirname (__file__), "..", "queries", k) : v
                for k, v in expectations.items () }
    for program, expected_output in queries.items ():
        ast = app.parse_file (program)
        statement = ast.statements
        """ This uses an unfortunate degree of knowledge about the implementation,
        both of the AST, and of theq query. Consider alternatives. """
        question = ast.statements[2].generate_questions (app)['message']
        nodes = question['query_graph']['nodes']
        edges = question['query_graph']['edges']
        # chemical_substance->gene->anatomical_entity->phenotypic_feature<-disease
        # node_index = { n['id'] : i for i, n in enumerate (nodes) }
        assert nodes['disease']['id'] == [disease_id]
        assert nodes['chemical_substance']['id'] == [chemical]
        assert edges['e1_chemical_substance_gene']['subject'] == 'chemical_substance'
        assert edges['e1_chemical_substance_gene']['object'] == 'gene'
        assert edges['e2_gene_anatomical_entity']['subject'] == 'gene'
        assert edges['e2_gene_anatomical_entity']['object'] == 'anatomical_entity'
        assert edges['e3_anatomical_entity_phenotypic_feature']['subject'] == 'anatomical_entity'
        assert edges['e3_anatomical_entity_phenotypic_feature']['object'] == 'phenotypic_feature'
        assert edges['e4_disease_phenotypic_feature']['object'] == 'phenotypic_feature'
        assert edges['e4_disease_phenotypic_feature']['subject'] == 'disease'

#####################################################
#
# Interpreter tests. Test the interpreter interface.
#
#####################################################
def test_interpreter_set (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test set statements by executing a few and checking values after. """
    print ("test_interpreter_set ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    tranql.resolve_names = False
    tranql.execute ("""
        -- Test set statements.
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/' """)

    variables = [ "disease", "max_p_value", "cohort", "icees.population_density_cluster", "gamma.quick" ]
    output = { k : tranql.context.resolve_arg (f"${k}") for k in variables }
    assert output['disease'] == "asthma"
    assert output['cohort'] == "COHORT:22"

def test_program (requests_mock):
    print ("test_program ()")
    mock_map = MockMap (requests_mock, "workflow-5")
    tranql = TranQL (options = {
        "asynchronous" : False,
        "resolve_names" : False,
        "recreate_schema": True
    })
    ast = tranql.execute ("""
    --
    -- Workflow 5
    --
    --   Modules 1-4: Chemical Exposures by Clinical Clusters
    --      For sub-clusters within the overall ICEES asthma cohort defined by
    --      differential population density, which chemicals are related to these
    --      clusters with a p_value less than some threshold?
    --
    --   Modules 5-*: Knowledge Graph Phenotypic Associations
    --      For chemicals produced by the first steps, what phenotypes are
    --      associated with exposure to these chemicals?
    --
    SET id_filters = "SCTID,rxcui,CAS,SMILES,umlscui"

    SELECT population_of_individual_organisms->drug
      FROM "/clinical/cohort/disease_to_chemical_exposure?provider=icees"
     WHERE EstResidentialDensity < '2'
       AND population_of_individual_organizms = 'x'
       AND cohort = 'all_patients'
       AND max_p_value = '0.1'
       SET '$.message.knowledge_graph.nodes.*.id' AS chemical_exposures

    SELECT chemical_substance->gene->biological_process->anatomical_entity
      FROM "/graph/gamma/quick"
     WHERE chemical_substance = $chemical_exposures
       SET knowledge_graph
    """)


    kg = tranql.context.resolve_arg("$knowledge_graph")
    assert "CHEBI:28177"  in kg['message']['knowledge_graph']['nodes']
    assert kg['message']['results'][0]['node_bindings']['chemical_substance'][0] == {"id": "CHEBI:28177"}


def test_unique_ids_for_repeated_concepts():
    tranql = TranQL()
    ast = tranql.parse(
        """
        SELECT g1:gene->g2:gene
        FROM '/schema'
        """
    )
    select_statement = ast.statements[0]
    question = select_statement.generate_questions(tranql)["message"]
    import json
    print(
        json.dumps(
            question, indent=4
        )
    )
    assert question['query_graph']['nodes'] == {
        "g1": {
            "category": "biolink:Gene"
        },
        "g2": {
            "category": "biolink:Gene"
        }
    }

def test_setting_values_for_repeated_concepts():
    tranql = TranQL()
    gene_list_1 = ['x:BRCA1', 'y:BRCA2']
    gene_list_2 = ['b:LTA', 'b:TNF']
    ast = tranql.parse(
        f"""
        SET brca={gene_list_1}
        SET tnf={gene_list_2}
        SELECT g1:gene->g2:gene
        FROM '/schema'
        WHERE g1 = $brca
        AND g2 = $tnf
        """
    )
    # exec set statments
    set_brcas = ast.statements[0]
    set_tnfs = ast.statements[1]
    set_brcas.execute(tranql)
    set_tnfs.execute(tranql)

    # generate questions
    question = ast.statements[2].generate_questions(tranql)["message"]
    question_nodes = question['query_graph']['nodes']
    assert set(question_nodes['g1']['id']) == set(gene_list_1)
    assert set(question_nodes['g2']['id']) == set(gene_list_2)


    # also test if direction is good
    for e in question['query_graph']['edges']:
        edge = question['query_graph']['edges'][e]
        assert edge['subject'] == 'g1'
        assert edge['object'] == 'g2'

def test_schema_can_talk_to_automat(requests_mock):
    set_mock(requests_mock, 'automat')
    config_file = os.path.join(os.path.dirname(__file__),"..","conf","schema.yaml")
    with open(config_file) as stream:
        schema_yml = yaml.load(stream, Loader=yaml.Loader)
    automat_url = 'http://localhost:8099' + schema_yml['schema']['automat']['registry_url'].rstrip('/') # servers as a check too if we even load it
    live_kps = requests.get(f'{automat_url}/registry').json()
    exclusion = schema_yml['schema']['automat']['exclude']
    live_kps = [x for x in live_kps if x not in exclusion]
    tranql = TranQL(options={
        'registry': True,
        'recreate_schema': True
    })
    ast = tranql.parse("""
            SELECT disease->d2:disease
              FROM '/schema'
        """)

    select = ast.statements[0]
    tranql_schema = select.planner.schema
    ## Test each KP is registered in schema
    for kp in live_kps:
        assert f'automat_{kp}' in tranql_schema.schema, f'KP Tranql schema entry not found for {kp}'
        ## Test if URL is refering to backplane url
        automat_kp_schema = tranql_schema.schema[f'automat_{kp}']
        assert automat_kp_schema['url'] == f'/graph/automat/{kp}', 'Automat backplane url incorrect'

def test_registry_disable():
    mock_schema_yaml = {
        'schema': {
            'automat': {
                'doc': 'docter docter, help me read this',
                'registry': 'automat',
                'registry_url': 'https://automat.renci.org',
                'url': '/graph/automat'

            }
        }
    }
    with patch('yaml.safe_load', lambda x: copy.deepcopy(mock_schema_yaml)):
        tranql_config = {}
        schema_factory = SchemaFactory('http://localhost:8099', use_registry=False, create_new=True,  update_interval=1, tranql_config=tranql_config)
        schema = schema_factory.get_instance()
        assert len(schema.schema) == 0

def test_registry_enabled(requests_mock):
    set_mock(requests_mock, 'automat')
    mock_schema_yaml = {
        'schema': {
            'automat': {
                'doc': 'docter docter, help me read this',
                'registry': 'automat',
                'registry_url': '/graph/automat/',
                'url': '/graph/automat'

            }
        }
    }

    with patch('yaml.safe_load', lambda x: copy.deepcopy(mock_schema_yaml)):
        tranql_config = {}
        schema_factory = SchemaFactory('http://localhost:8099', use_registry=True, update_interval=1, create_new=True, tranql_config=tranql_config)
        schema = schema_factory.get_instance()
        assert len(schema.schema) > 1


def test_registry_adapter_automat():
    from tranql.tranql_schema import RegistryAdapter

    # let pretend automat url is automat and we will mask what we expect to be called
    # since there is no real logic here we just have to make sure apis are called

    with requests_mock.mock() as mock_server:
        mock_server.get('http://automat/registry', json=['kp1'])
        expected_response = ['lets pretend this was a schema']
        mock_server.get('http://automat/kp1/predicates', json=expected_response)
        ra = RegistryAdapter()
        response = ra.get_schemas('automat', 'http://automat')
        assert 'automat_kp1' in response
        assert 'schema' in response['automat_kp1']
        assert 'url' in response['automat_kp1']
        assert response['automat_kp1']['schema'] == expected_response


def test_schema_should_not_change_once_initilalized():
    """
    Scenario: In a registry aware schema,
    UserObject initializes schema object.
    Schema object now has entries from registry(eg. automat).
    UserObject starts work on that schema. During this time,
    Schema instance is updated by it's thread and some entries on
    the schema might have changed. When UserObject looks back at the schema
    it's different
    """

    mock_schema_yaml = {
        'schema':{
            'automat': {
                'doc': 'docter docter, help me read this',
                'registry': 'automat',
                'registry_url': '/graph/automat',
                'url': '/graph/automat'

            }
        }
    }
    mock_schema_response = {
        'kp1': {
            'type1': {
                'type2':[
                    'related_to'
                ]
            }
        },
        'kp2': {
            'type99': {
                'type300': [
                    'related_to'
                ]
            }
        }
    }


    with patch('yaml.safe_load', lambda x: copy.deepcopy(mock_schema_yaml)):
        update_interval = 1
        backplane = 'http://localhost:8099'

        with requests_mock.mock() as m:
            # setup mock kps
            kps = ['kp1', 'kp2']
            for kp in kps:
                m.get(f'{backplane}/graph/automat/{kp}/predicates', json=mock_schema_response[kp])
            # say registry returns kp1 on first call
            m.get(f'{backplane}/graph/automat/registry', json=['kp1'])
            # here some Tranql objects have this instance.
            schema_factory = SchemaFactory(
                backplane=backplane,
                use_registry=True,
                update_interval=update_interval,
                create_new=True,
                tranql_config={}
            )
            schema1 = schema_factory.get_instance()
            schema2 = schema_factory.get_instance()
            # Doing something on second  schema instance should not affect the first.
            schema2.schema['Lets add something'] = {'add some thing': 'dsds'}
            assert 'Lets add something' not in schema1.schema

        with requests_mock.mock() as m:
            # setup mock kps
            kps = ['kp1', 'kp2']
            for kp in kps:
                m.get(f'{backplane}/graph/automat/{kp}/predicates', json=mock_schema_response[kp])
            # Now we change what registry returns and wait for update
            m.get(f'{backplane}/graph/automat/registry', json=['kp2'])
            # lets wait for next updated and request a new object
            # testing to see if our new request results will affect the
            # the original schema
            time.sleep(update_interval + 1) # sleeping to ensure update thread is working
            schema2 = schema_factory.get_instance()
            # original reference to Schema should be different from second.
            assert schema1 != schema2

# ---------------- Knowledge map merge tests ----------



def test_find_paths_linear_graph():
    edge_set_1 = ['edge1', 'edge2', 'edge3']
    edge_set_2 =  ['edge2']
    linear_graph = {
        'node1': {
            'node2': edge_set_1
        },
        'node2': {
            'node3': edge_set_2
        }
    }
    paths = []
    find_all_paths(
        graph=linear_graph,
        start='node1',
        edge=None, # first incoming edge
        visited=set(),
        stack=[],
        paths=paths
    )
    assert len(paths) == 1
    # not the structure of paths is
    # [[node, edge], [node, edge]....]
    # with the notion that each node is connected with the previous edge with the edge in the list it exists
    # check if first node has no incoming edges
    assert paths[0][0][1] == None
    # check if each node exists
    assert set(['node1','node2','node3']) == set(map(lambda item: item[0], paths[0]))
    edges_from_path = list(map(lambda item: item[1], paths[0]))
    assert edge_set_1 in edges_from_path
    assert edge_set_2 in edges_from_path

def test_find_all_paths_branching_graph():
    # things get tricky here
    edge_set= [
        ['e1', 'e2'],
        ['e3', 'e4'],
        ['eee'],
        ['e232'],
        ['edge'],
        ['edge09099']
    ]

    branching_graph_diff_terminal_nodes = {
        'a': {'b': edge_set[0]},
        'b': {
            'c': edge_set[1],
            'd': edge_set[2]
        },
        'c': {'e': edge_set[3]},
        'd': {'f': edge_set[4]}
    }
    paths = []
    find_all_paths(
        graph=branching_graph_diff_terminal_nodes,
        start='a',
        edge=None,
        visited=set(),
        stack=[],
        paths=paths
    )
    # we have two paths
    # a - b - c - e, a - b - d - f
    assert len(paths) == 2
    nodes_paths = list(map(lambda x: set(map(lambda item: item[0], x)), paths))
    assert set(['a','b','c','e']) in nodes_paths
    assert set(['a','b','d', 'f']) in nodes_paths

    # branching with same terminal nodes
    # a- b- c- e , a - b - d -e
    branching_graph_same_terminal_nodes = branching_graph_diff_terminal_nodes
    branching_graph_same_terminal_nodes['d'] = {
        'e': edge_set[4]
    }
    paths = []
    find_all_paths(
        graph=branching_graph_same_terminal_nodes,
        start='a',
        edge=None,
        visited=set(),
        stack=[],
        paths=paths
    )
    assert len(paths) == 2
    nodes_paths = list(map(lambda x: set(map(lambda item: item[0], x)), paths))
    assert set(['a', 'b', 'c', 'e']) in nodes_paths
    assert set(['a', 'b', 'd', 'e']) in nodes_paths


def test_connect_graph_should_return_same_knowledge_map_for_single_response ():
    q_graph = {
        'nodes': {
            'n1': {'category': ['tp1']},
            'n2': {'category': ['tp2']},
        },
        'edges': {
            'e1': {'subject': 'n1', 'object': 'n2'},
        }
    }
    k_graph = {
        'nodes': {
                "some:curie": {
                    'category': ['tp1'],
                    'name': 'first node'
                },
                "some:curie2": {
                    'category': ['tp2'],
                    'name': 'second node'
                }
        },
        'edges': {
            "e1-kg-id": {"source": "some:curie", "target": "some:curie2", "predicate": "pred:1"},
            "e2-kg-id": {"source": "some:curie", "target": "some:curie2", "predicate": "pred:2"}
        }
    }
    k_map = [
        {
            'node_bindings': {
                'n1': [{"id":'some:curie'}],
                'n2': [{"id": 'some:curie2'}]
            },
            'edge_bindings': {
                'e1': [{"id": 'e1-kg-id'}]
            }
        }
    ]
    full_response = {
        'knowledge_graph': k_graph,
        'query_graph': q_graph,
        'results': k_map
    }
    merged_k_map = connect_knowledge_maps([full_response])
    assert len(merged_k_map) == len(k_map)
    assert merged_k_map[0]['node_bindings'] == k_map[0]['node_bindings']
    assert merged_k_map[0]['edge_bindings'] == k_map[0]['edge_bindings']

def test_merge_two_responses_connected_one_after_the_other():
    q_G_1 = {
        'nodes': {"n0": {'id': 'n0'}, "n1":{'id': 'n1'}},
        'edges': {'e1': {'subject': 'n0', 'object': 'n1'}}
    }
    q_G_2 = {
        'nodes': {"n1": {'id': 'n1'}, "n2":{'id': 'n2'}},
        'edges': {"e1-1": {'id': 'e1-1', 'subject': 'n1', 'object': 'n2'}}
    }
    k_map_1 = [
        {
            'node_bindings': {'n0': [{"id":'kg_id_of_n0'}], 'n1': [{"id":'kg_id_of_n1'}]},
            'edge_bindings': {'e1': [{"id": 'kg_id_of_e1'}]}
        }
    ]
    k_map_2 = [
        {
            'node_bindings': {'n1': [{"id": 'kg_id_of_n1'}], 'n2': [{"id": 'kg_id_of_n1'}]},
            'edge_bindings': {'e1-1': [{"id":'kg_id_of_e1-1'}]}
        }
    ]
    response = connect_knowledge_maps([{
        'query_graph': q_G_1,
        'results': k_map_1,
    }, {
        'query_graph': q_G_2,
        'results': k_map_2
    }])
    assert len(response) == 1
    merged_answer_nodes = response[0]['node_bindings']
    merged_answer_edges = response[0]['edge_bindings']
    assert 'n0' in merged_answer_nodes and  merged_answer_nodes['n0'] == k_map_1[0]['node_bindings']['n0']
    assert 'n1' in merged_answer_nodes and  merged_answer_nodes['n1'] == k_map_1[0]['node_bindings']['n1']
    assert 'n2' in merged_answer_nodes and  merged_answer_nodes['n2'] == k_map_2[0]['node_bindings']['n2']

    assert 'e1' in merged_answer_edges and merged_answer_edges['e1'] == k_map_1[0]['edge_bindings']['e1']
    assert 'e1-1' in merged_answer_edges and merged_answer_edges['e1-1'] == k_map_2[0]['edge_bindings']['e1-1']


def test_connected_q_graph_disconnected_kg_map():
    q_G_1 = {
        'nodes': {"n0":{'id': 'n0'}, 'n1':{'id': 'n1'}},
        'edges': {'e1': {'id': 'e1', 'subject': 'n0', 'object': 'n1'}}
    }
    q_G_2 = {
        'nodes': {'n1':{'id': 'n1'}, 'n1': {'id': 'n2'}},
        'edges': {'e1-1': {'id': 'e1-1', 'subject': 'n1', 'object': 'n2'}}
    }
    k_map_1 = [
        {
            'node_bindings': {'n0': [{'id': 'kg_id_of_n0'}], 'n1': [{'id':'kg_id_of_n1'}]},
            'edge_bindings': {'e1': [{'id': 'kg_id_of_e1'}]}
        }
    ]
    k_map_2 = [
        {
            'node_bindings': {'n1': [{'id': 'HEREISWHEREDISCONNECTIONIS'}], 'n2': [{'id': 'kg_id_of_n1'}]},
            'edge_bindings': {'e1-1': [{'id': 'kg_id_of_e1-1'}]}
        }
    ]
    response = connect_knowledge_maps([{
        'query_graph': q_G_1,
        'results': k_map_1,
    }, {
        'query_graph': q_G_2,
        'results': k_map_2
    }])
    assert len(response) == 2
    # each binding should have 2 nodes and single edge
    for answer in response:
        assert len(answer['node_bindings']) == 2
        assert len(answer['edge_bindings']) == 1

def test_partials_disconnected_and_connected():
    """
    a:A--- b:B ---- c:C ----- d:D ---- e:E  (RESP 1 & 2)
           |                 /
           f:C ------------g:G
    a1:A--- b1:B              {RESP 3)
    a2:A --- b:B   (RESP 4)(this should contain paths continued from b
    #####
    P1 : a->b->c->d->e
    p2 : a->b->f->g->d->e
    p3 : a1->b1
    p4 : a2->b->c->d->e
    p5: a2->b->f->g-d->e
    """
    q_g_1 = {
        'nodes': {
            'A': {'id': 'A', 'type': 'A'},
            'B': {'id': 'B', 'type': 'B'},
            'C': {'id': 'C', 'type': 'C'},
            'D': {'id': 'D', 'type': 'D'},
            'E': {'id': 'E', 'type': 'E'}
        }, 'edges': {
            'e-A-B': {'id': 'e-A-B', 'subject': 'A', 'object':'B'},
            'e-B-C': {'id': 'e-B-C', 'subject': 'B', 'object': 'C'},
            'e-C-D': {'id': 'e-C-D', 'subject': 'C', 'object': 'D'},
            'e-D-E': {'id': 'e-D-E', 'subject': 'D', 'object': 'E'}
        }
    }
    q_g_2 = {
        'nodes': {
            'B': {'id': 'B', 'type': 'B'},
            'C': {'id': 'C', 'type': 'C'},
            'G': {'id': 'G', 'type': 'G'},
            'D': {'id': 'D', 'type': 'D'}
        },
        'edges': {
            'e-B-C': {'id': 'e-B-C', 'subject': 'B', 'object': 'C'},
            'e-C-G': {'id': 'e-C-G', 'subject': 'C', 'object': 'G'},
            'e-G-D': {'id': 'e-G-D', 'subject': 'G', 'object': 'D'}
        }
    }
    q_g_3 = {
        'nodes':{
            'A': {'id': 'A', 'type': 'A'},
            'B': {'id': 'B', 'type': 'B'}
        },
        'edges': {
            'e-A-B':{'id': 'e-A-B', 'subject': 'A', 'object': 'B'}
        }
    }
    q_g_4 = {
        'nodes': {
            'A': {'id': 'A', 'type': 'A'},
            'B': {'id': 'B', 'type': 'B'}
        },
        'edges': {
            'e-A-B': {'id': 'e-A-B', 'subject':'A', 'object': 'B'}
        }
    }

    # Lets make some graphs that look like the above ones

    k_map_1 = [{'node_bindings': {'A': [{'id': 'a'}],
                                  'B': [{'id': 'b'}],
                                  'C': [{'id': 'c'}],
                                  'D': [{'id': 'd'}],
                                  'E': [{'id': 'e'}]},
                'edge_bindings': {'e-A-B': [{'id': 'e-a-b'}],
                                  'e-B-C': [{'id': 'e-b-c'}],
                                  'e-C-D': [{'id': 'e-c-d'}],
                                  'e-D-E': [{'id': 'e-d-e'}]}}]  # a - b - c - d -e
    k_map_2 = [{'node_bindings': {'B': [{'id': 'b'}],
                                  'C': [{'id': 'f'}],
                                  'G': [{'id': 'g'}],
                                  'D': [{'id': 'd'}]},
                'edge_bindings': {'e-B-C': [{'id': 'e-b-f'}],
                                  'e-C-G': [{'id': 'e-c-g'}],
                                  'e-G-D': [{'id': 'e-g-d'}]}}]  # b - f -  g - d
    k_map_3 = [{'node_bindings': {'A': [{'id': 'a1'}], 'B': [{'id': 'b1'}]},
                'edge_bindings': {'e-A-B': [{'id': 'e-a1-b1'}]}}]
    k_map_4 = [{'node_bindings': {'A': [{'id': 'a2'}], 'B': [{'id': 'b'}]},
                'edge_bindings': {'e-A-B': [{'id': 'e-a2-b'}]}}]
    responses = [
        {'query_graph': q_g_1, 'results': k_map_1},
        {'query_graph': q_g_2, 'results': k_map_2},
        {'query_graph': q_g_3, 'results': k_map_3},
        {'query_graph': q_g_4, 'results': k_map_4}
    ]
    merged_paths = connect_knowledge_maps(responses)
    assert len(merged_paths) == 5
    # check path a->b->c->d->e
    p1 = {'node_bindings': {'A': [{'id': 'a'}],
                               'B': [{'id': 'b'}],
                               'C': [{'id': 'c'}],
                               'D': [{'id': 'd'}],
                               'E': [{'id': 'e'}]},
                              'edge_bindings': {'e-A-B': [{'id': 'e-a-b'}],
                               'e-B-C': [{'id': 'e-b-c'}],
                               'e-C-D': [{'id': 'e-c-d'}],
                               'e-D-E': [{'id': 'e-d-e'}]},
                                    'score': 0
    }
    assert p1 in merged_paths
    p2 = {'node_bindings': {'A': [{'id': 'a'}],
                            'B': [{'id': 'b'}],
                            'C': [{'id': 'f'}],
                            'G': [{'id': 'g'}],
                            'D': [{'id': 'd'}],
                            'E': [{'id': 'e'}]},
          'edge_bindings': {'e-A-B': [{'id': 'e-a-b'}],
                            'e-B-C': [{'id': 'e-b-f'}],
                            'e-C-G': [{'id': 'e-c-g'}],
                            'e-G-D': [{'id': 'e-g-d'}],
                            'e-D-E': [{'id': 'e-d-e'}]},
          'score': 0
          }
    # check path p2: a:A->b:B->f:C->g:G->d:D->e:E
    assert p2 in merged_paths
    # Check for p3
    # p3: a1->b1
    p3 = {'node_bindings': {'A': [{'id': 'a1'}], 'B': [{'id': 'b1'}]},
          'edge_bindings': {'e-A-B': [{'id': 'e-a1-b1'}]},
          'score': 0
          }
    assert  p3 in merged_paths

    # check p4
    # p4: a2->b->c->d->e
    p4 = {'node_bindings': {'A': [{'id': 'a2'}],
                            'B': [{'id': 'b'}],
                            'C': [{'id': 'c'}],
                            'D': [{'id': 'd'}],
                            'E': [{'id': 'e'}]},
          'edge_bindings': {'e-A-B': [{'id': 'e-a2-b'}],
                            'e-B-C': [{'id': 'e-b-c'}],
                            'e-C-D': [{'id': 'e-c-d'}],
                            'e-D-E': [{'id': 'e-d-e'}]}, 'score': 0
        }
    assert  p4 in merged_paths
    # check p5
    # p5: a2->b->f->g - d->e
    p5 = {'node_bindings': {'A': [{'id': 'a2'}],
                            'B': [{'id': 'b'}],
                            'C': [{'id': 'f'}],
                            'D': [{'id': 'd'}],
                            'E': [{'id': 'e'}],
                            'G': [{'id': 'g'}]},
          'edge_bindings': {'e-A-B': [{'id': 'e-a2-b'}],
                            'e-B-C': [{'id': 'e-b-f'}],
                            'e-C-G': [{'id': 'e-c-g'}],
                            'e-G-D': [{'id': 'e-g-d'}],
                            'e-D-E': [{'id': 'e-d-e'}]}, 'score': 0
          }
    assert p5 in merged_paths


@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_merge_preserves_edge_ids(GraphInterfaceMock):
    kg = {
        "message": {
            'query_graph': {
                'nodes': {
                    "n0": {'id': 'n0', 'category': ['type1']},
                    "n1": {'id': 'n1', 'category': ['type2']}
                },
                'edges': {
                    "e0": {'id': 'e0', 'subject': 'n0', 'object': 'n1'}
                }
            },
            'knowledge_graph': {
                'nodes': {
                    "CURIE:1": {'id': 'CURIE:1', 'name': 'Node 1'},
                    "curie:2": {'id': 'curie:2', 'name': 'another node'},
                    "curie:3": {'id': 'curie:3', 'name': 'third node'}
                },
                'edges': {
                    "curie1:curie2": {'id': 'curie1:curie2', 'predicate': 'related_to', 'subject': 'CURIE:1',
                                      'object': 'curie:2'},
                    "curie1:curie2Duplicate": {'id': 'curie1:curie2Duplicate', 'predicate': 'related_to',
                                               'subject': 'CURIE:1', 'object': 'curie:2'},
                    "curie1:curie3": {'id': 'curie1:curie3', 'predicate': 'related_to', 'subject': 'CURIE:1',
                                      'object': 'curie:3'}
                }
            },
            'results': [{'node_bindings': {'n0': [{'id': 'CURIE:1'}], 'n1': [{'id': 'curie:2'}]},
                         'edge_bindings': {'e0': [{'id': 'curie1:curie2'}]}},
                        {'node_bindings': {'n0': [{'id': 'CURIE:1'}], 'n1': [{'id': 'curie:2'}]},
                         'edge_bindings': {'e0': [{'id': 'curie1:curie2Duplicate'}]}},
                        {'node_bindings': {'n0': [{'id': 'CURIE:1'}], 'n1': [{'id': 'curie:3'}]},
                         'edge_bindings': {'e0': [{'id': 'curie1:curie3'}]}}]
        }
    }
    tranql = TranQL()
    responses = [kg]
    select_statement = SelectStatement(tranql)
    result = select_statement.merge_results(responses)
    edges = result["message"]['knowledge_graph']['edges']
    all_edge_ids = set(e for e in edges)
    for answer_binding in result["message"]['results']:
        e_b = answer_binding['edge_bindings']
        edge_ids = reduce(lambda x, y : x + y, map(lambda x: e_b[x], e_b), [])
        for i in edge_ids:
            assert i['id'] in all_edge_ids, print(edge_ids)

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_merge_should_preserve_score(GraphInterfaceMock):
    """
    Once  a knowledge response is merged
    :return:
    """
    query_graph = {
        'nodes': {
            'A': {'id': 'A', 'type': 'A'},
            'B': {'id': 'B', 'type': 'B'}
        }, 'edges': {
            'e-A-B': {'id': 'e-A-B', 'subject': 'A', 'object':'B'}
        }
    }
    knowledge_graph = {
        'nodes': {
            'KG_ID_A': {'id': 'KG_ID_A', 'name': 'node A from kg'},
            'KG_ID_B': {'id': 'KG_ID_B', 'name': 'node B from kg'},
            'KG_ID_AA': {'id': 'KG_ID_AA', 'name': 'node AA from kg'},
            'KG_ID_BB': {'id': 'KG_ID_BB', 'name': 'node BB from kg'},
        },
        'edges': {
            'KG_ID_A_B':{'id': 'KG_ID_A_B', 'predicate': 'related_to', 'subject': 'KG_ID_A', 'object': 'KG_ID_B'},
            'KG_ID_AA_BB':{'id': 'KG_ID_AA_BB', 'predicate': 'related_to', 'subject': 'KG_ID_AA', 'object': 'KG_ID_BB'},
        }
    }
    knowledge_map = [
        {'node_bindings': {'A': [{'id': 'KG_ID_A'}], 'B': [{'id': 'KG_ID_B'}]},
         'edge_bindings': {'e-A-B': [{'id':'KG_ID_A_B'}]}, "score": 1},
        {'node_bindings': {'A': [{'id': 'KG_ID_AA'}], 'B': [{'id': 'KG_ID_BB'}]},
         'edge_bindings': {'e-A-B': [{'id': 'KG_ID_AA_BB'}]}, "score": 2}
    ]
    tranql = TranQL()
    responses = [{"message": {
        'query_graph': query_graph,
        'results': knowledge_map,
        'knowledge_graph': knowledge_graph
    }}]
    select_statement = SelectStatement(tranql)
    result = select_statement.merge_results(responses)
    for answer in result['message']['results']:
        assert 'score' in answer
        assert answer['score'] == 1 or answer['score'] == 2

def xtest_merged_node_ids_should_be_updated_in_knowledge_map():
    "No longer needed we are not merging based on equvalent identifiers ids "
    tranql = TranQL()
    select_statement = SelectStatement(tranql)
    q_graph = {
        'nodes': [{'id': 'n0', 'type': 'type1'}, {'id': 'n1', 'type': 'type2'}],
        'edges': [{'id': 'e0', 'type':'related_to', 'source_id':'n0', 'target_id': 'n1'}]
    }
    kg_1 = {
        'nodes': {
            'kg_id_1': {'id': 'kg_id_1', 'equivalent_identifiers': ['kg_id_1', 'curie1'], 'name': 'kg 1 node'},
            'kg_id_2': {'id': 'kg_id_2', 'equivalent_identifiers': ['kg_id_2', 'curie2'], 'name': 'kg 2 node'},
            'kg_id_3': {'id': 'kg_id_3', 'equivalent_identifiers': ['kg_id_3', 'curie3'], 'name': 'kg 3 node'}
        },
        'edges': {
            'e_kg_id_1': {'id': 'e_kg_id_1', 'source_id': 'kg_id_1', 'target_id': 'kg_id_2', 'type': 'related_to'},
            'e_kg_id_2': {'id': 'e_kg_id_2', 'source_id': 'kg_id_1', 'target_id': 'kg_id_3', 'type': 'related_to'}
        }
    }
    kg_2 = {
        'nodes': [
            {'id': 'kg_id_22', 'equivalent_identifiers': ['kg_id_22', 'curie2'], 'name': 'kg 2 node'},
            {'id': 'kg_id_3', 'equivalent_identifiers': ['kg_id_3', 'curie3'], 'name': 'kg 3 node'}
        ],
        'edges': [
            # links 22 with 3 so we exepect 22 to convert to 1 then 1 liked with 3
            {'id': 'e_kg_id_22', 'source_id': 'kg_id_22', 'target_id': 'kg_id_3', 'type': 'related_to'}
        ]
    }
    knowledge_map_1  = [
        {'node_bindings': {'n0': 'kg_id_1', 'n1': 'kg_id_2'}, 'edge_bindings': {'e0': 'e_kg_id_1'}},
        {'node_bindings': {'n0': 'kg_id_1', 'n1': 'kg_id_3'}, 'edge_bindings': {'e0': 'e_kg_id_2'}}
    ]
    knowledge_map_2 = [
        {'node_bindings': {'n0': 'kg_id_1', 'n1': 'kg_id_2'}, 'edge_bindings': {'e0': 'e_kg_id_11'}},
        {'node_bindings': {'n0': 'kg_id_22', 'n1': 'kg_id_3'}, 'edge_bindings': {'e0': 'e_kg_id_22'}}
    ]

    responses = [
        {'question_graph': q_graph, 'knowledge_map': knowledge_map_1, 'knowledge_graph': kg_1},
        {'question_graph': q_graph, 'knowledge_map': knowledge_map_2, 'knowledge_graph': kg_2},
    ]
    # paths we expect are
    # kg_id_1 -> kg_id_2 -> kg_id3
    # kg_id_1 -> kg_id_3

    merged_response = select_statement.merge_results(responses, tranql, q_graph, ['n0','n1'])
    assert len(merged_response['knowledge_graph']['nodes']) == 3 #
    assert len(merged_response['knowledge_graph']['edges']) == 3

    # check if ids are all goood and that equivalnt ids are merged (this would be like testing properties are merged)

    nodes_by_id = {node['id'] : node for node in merged_response['knowledge_graph']['nodes']}
    edges_by_id = {edge['id']: edge for edge in merged_response['knowledge_graph']['edges']}

    assert 'kg_id_1' in nodes_by_id
    assert 'kg_id_3' in nodes_by_id
    assert 'kg_id_2' in nodes_by_id
    # things get interesting here , need to check if all eq ids are being merged for kg_id_2
    assert set(nodes_by_id['kg_id_2']['equivalent_identifiers']) == set(['kg_id_2', 'curie2', 'kg_id_22'])

    # edges test
    assert 'e_kg_id_1' in edges_by_id
    assert 'e_kg_id_2' in edges_by_id
    assert 'e_kg_id_22' in edges_by_id
    # assert if e_kg_id_22 source id is updated
    assert edges_by_id['e_kg_id_22']['source_id'] == 'kg_id_2'

    # check knowledge map  updates
    # we exepect 3 answers kg_id_1:n0 -> kg_id_2:n1
    # and kg_id_1:n0 -> kg_id_3:n1
    # and kg_id_2:n0 -> kg_id_3:n1
    assert len(merged_response['knowledge_map']) == 3
    # make sure our edge_bindings are sane
    answers = merged_response['knowledge_map']
    edge_bindings_all = map(lambda answer: answer['edge_bindings']['e0'], answers)
    expected_edges = ['e_kg_id_11', 'e_kg_id_2', 'e_kg_id_22']
    for i in edge_bindings_all:
        index = expected_edges.index(i)
        expected_edges.pop(index)
    assert expected_edges == []

    # last test is to see if node bindings are also updated,
    # note that in the second response we made up we had a node binding pointing to kg_id_22 we ensure that
    # its matching edge edge_id_22 is present along side and the node binding is pointing to kg_id_2
    node_bindings_by_edge_kg_id = {
        a['edge_bindings']['e0']: a['node_bindings']
        for a in answers
    }
    # note merging converts curies to lists
    assert node_bindings_by_edge_kg_id['e_kg_id_11']['n0'] == ['kg_id_1']
    assert node_bindings_by_edge_kg_id['e_kg_id_11']['n1'] == ['kg_id_2']
    # this was kg_id_22
    assert node_bindings_by_edge_kg_id['e_kg_id_22']['n0'] == ['kg_id_2']
    assert node_bindings_by_edge_kg_id['e_kg_id_22']['n1'] == ['kg_id_3']
    assert node_bindings_by_edge_kg_id['e_kg_id_2']['n0'] == ['kg_id_1']
    assert node_bindings_by_edge_kg_id['e_kg_id_2']['n1'] == ['kg_id_3']

@patch("PLATER.services.util.graph_adapter.GraphInterface._GraphInterface")
def test_redis_graph_cypher_options(GraphInterfaceMock):
    """doc: |
      Roger is a knowledge graph built by aggregeting several kgx formatted knowledge graphs from several sources.
    url: "redis:"
    redis: true
    redis_connection_params:
      host: localhost
      port: 6380"""

    mock_schema_yaml = {
        'schema':{
            'redis': {
                'doc': 'Red is a color but REDIS?',
                'url': 'redis:',
                'redis': True,
                'redis_connection_params': {
                    'host': 'local',
                    'port': 6379
                }
            }
        }
    }

    class graph_Inteface_mock:
        def __init__(self, limit , skip, options_set):
            self.limit = limit
            self.skip  = skip
            self.options_set = options_set

        async def answer_trapi_question(self, message, options={}):
            assert message
            if self.options_set:
                assert options
                assert options['limit'] == self.limit
                assert options['skip'] == self.skip
            else:
                assert options == {}
            return {}

    # we override the schema
    tranql = TranQL()
    with patch('yaml.safe_load', lambda x: copy.deepcopy(mock_schema_yaml)):
        # clean up schema singleton
        update_interval = 1
        backplane = 'http://localhost:8099'
        schema_factory = SchemaFactory(
            backplane=backplane,
            use_registry=False,
            update_interval=update_interval,
            create_new=True,
            tranql_config={}
        )
        tranql.schema = schema_factory.get_instance()
        with patch('PLATER.services.util.graph_adapter.GraphInterface.instance', graph_Inteface_mock(limit=20, skip=100, options_set=True)):
            ast = tranql.parse(
                """
                SELECT g1:gene->g2:gene
                FROM 'redis:test'
                where limit = 20 and skip = 100
                """
            )
            select_statement = ast.statements[0]
            select_statement.execute(interpreter=tranql)

        with patch('PLATER.services.util.graph_adapter.GraphInterface.instance', graph_Inteface_mock(limit=20, skip=100, options_set=False)):
            ast = tranql.parse(
                """
                SELECT g1:gene->g2:gene
                FROM 'redis:test'
                """
            )
            select_statement = ast.statements[0]
            select_statement.execute(interpreter=tranql)