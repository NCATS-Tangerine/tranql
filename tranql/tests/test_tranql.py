import json
import pytest
import os
import itertools
import requests
import yaml
from pprint import pprint
from deepdiff import DeepDiff
from functools import reduce
from tranql.main import TranQL
from tranql.main import TranQLParser, set_verbose
from tranql.tranql_ast import SetStatement, SelectStatement, CustomFunction
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.tests.mocks import MockHelper
from tranql.tests.mocks import MockMap
from tranql.tranql_schema import SchemaFactory
import requests_mock
from unittest.mock import patch
import copy, time

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

def test_parse_predicate (requests_mock):
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

def test_parse_function (requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing and resolving function values (including nested) """
    # Create a custom function that concats two strings
    @CustomFunction.custom_function
    def concat_strings(str_a, str_b):
        return str_a + str_b

    # Create a function that returns "asth"
    @CustomFunction.custom_function
    def get_asthma():
        return "asth"

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


def test_parse_set (requests_mock):
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

def test_parse_set_with_comment (requests_mock):
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

def test_parse_select_simple (requests_mock):
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

def test_parse_select_complex (requests_mock):
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

def test_parse_query_with_repeated_concept (requests_mock):
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
    questions = ast.statements[0].generate_questions (app)
    assert questions[0]['question_graph']['nodes'][0]['curie'] == 'MONDO:0004979'
    assert questions[0]['question_graph']['nodes'][0]['type'] == 'disease'
def test_ast_generate_questions_from_list():
    tranql = TranQL()
    curie_list = ['chebi:123', 'water']
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
    questions = ast.statements[1].generate_questions(tranql)
    question_nodes = reduce(lambda x, y: x + y,
                            list(
                                map(lambda question: question['question_graph']['nodes'],
                                questions)), [])
    question_curies = list(map(lambda x: x['curie'], filter(lambda node: node['type'] == 'chemical_substance', question_nodes)))
    assert len(set(question_curies)) == 2
    assert len(questions) == 2
    for curie in question_curies:
        assert curie in curie_list


    # Multiple variable setting
    chemicals = curie_list
    gene_list = ['BRAC1', 'BRAC2']
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

    questions = select_statement.generate_questions(tranql)
    # get all chemical and genes


    grab_ids = lambda node_type: list(
        # using SET to select unique ids only and casting back to list
        # grabs ids from questions based on node type
        set(reduce(
            lambda acc, question_graph: acc + list(map(
                lambda node: node['curie'],
                filter(lambda node: node['type'] == node_type, question_graph['nodes'])
            )),
            map(
                lambda question: question['question_graph'],
                questions
            ),
            []
        ))
    )
    chemicals_ids = grab_ids('chemical_substance')
    gene_ids = grab_ids('gene')
    assert len(questions) == 4
    chemicals.sort()
    chemicals_ids.sort()
    gene_ids.sort()
    gene_list.sort()
    assert_lists_equal(chemicals_ids, chemicals)
    assert_lists_equal(gene_list, gene_ids)

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
    questions = select_statememt.generate_questions(tranql)

    question_nodes = reduce(
        lambda x, y: x + y,
        list(
            map(
                lambda x: x['question_graph']['nodes'],
                questions
            )
        ), [])
    # filter out gene curies from the questions
    gene_curies = list(map(lambda node: node['curie'], filter(lambda node: node['type'] == 'gene', question_nodes)))
    # we should have two questions
    assert len(questions) == 2
    gene_curies.sort()
    curies.sort()
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
    backwards_questions = statements[1].generate_questions(tranql)

    assert len(backwards_questions) == 1
    assert len(backwards_questions[0]["question_graph"]["edges"]) == 1
    assert backwards_questions[0]["question_graph"]["edges"][0]["source_id"] == "microRNA"
    assert backwards_questions[0]["question_graph"]["edges"][0]["target_id"] == "biological_process"
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

    assert_lists_equal(node["reasoner"],["robokop"])

    assert_lists_equal(edge["reasoner"],["robokop"])
    assert_lists_equal(edge["source_database"],["unknown"])
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
    question = select.generate_questions(tranql)[0]["question_graph"]

    assert len(question["edges"]) == 1

    assert "type" in question["edges"][0]
    assert question["edges"][0]["type"] == "treats"
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
def test_ast_merge_knowledge_maps (requests_mock):
    set_mock(requests_mock, "workflow-5")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    tranql.asynchronous = False
    tranql.resolve_names = False
    ast = tranql.parse ("""
        select chemical_substance->disease->gene
          from "/schema"
         where chemical_substance="CHEMBL:CHEMBL3"
    """)

    # select = ast.statements[0]
    # statements = select.plan (select.planner.plan (select.query))
    # print(statements[0].query.order)

    # (select.execute_plan(tranql))

    responses = [
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                    'chemical_substance' : 'CHEBI:100',
                        'disease' : 'MONDO:50'
                    },
                    'edge_bindings' : {
                        'e0' : 'ROOT_EDGE'
                    }
                }
            ],
            'question_order' : ['chemical_substance','disease']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'disease' : 'MONDO:50',
                        'gene' : 'HGNC:1',
                        'metabolite' : 'KEGG:C00017'
                    },
                    'edge_bindings' : {
                        'e1' : 'TEST_EDGE'
                    }
                }
            ],
            'question_order' : ['disease','gene','metabolite']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'disease' : 'MONDO:50',
                        'gene' : 'HGNC:1',
                        'metabolite' : 'KEGG:FOOBAR'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['disease','gene','metabolite']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'metabolite' : 'KEGG:FOOBAR',
                        'protein' : 'UniProtKB:TESTING'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['metabolite','protein']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'metabolite' : 'KEGG:C00017',
                        'protein' : 'UniProtKB:Q9NZJ5'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['metabolite','protein']
        }
    ]

    merged = SelectStatement.connect_knowledge_maps(responses,[
        'chemical_substance',
        'disease',
        'gene',
        'metabolite',
        'protein'
    ])

    assert_lists_equal(ordered(merged), ordered([
        {
            "node_bindings" : {
                "chemical_substance" : "CHEBI:100",
                "disease" : "MONDO:50",
                "gene" : "HGNC:1",
                "metabolite" : "KEGG:FOOBAR",
                "protein" : "UniProtKB:TESTING"
            },
            "edge_bindings" : {
                "e0" : "ROOT_EDGE"
            }
        },
        {
            "node_bindings" : {
                "chemical_substance" : "CHEBI:100",
                "disease" : "MONDO:50",
                "gene" : "HGNC:1",
                "metabolite" : "KEGG:C00017",
                "protein" : "UniProtKB:Q9NZJ5"
            },
            "edge_bindings" : {
                "e0" : "ROOT_EDGE",
                "e1" : "TEST_EDGE",
            }
        }
    ]))

    # print(json.dumps(merged,indent=2))

def test_ast_merge_results (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- Results from the query plan are being merged together correctly
    """
    print("test_ast_merge_answers ()")
    tranql = TranQL (options={
        'recreate_schema': True
    })
    tranql.resolve_names = False
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)

    select = ast.statements[0]

    # What is the proper format for the name of a mock file? This should be made into one
    mock_responses = [
        {
            'knowledge_graph': {
                'nodes': [
                    {'id': 'CHEBI:28177', 'type': 'chemical_substance'},
                    {'id': 'HGNC:2597', 'type': 'gene'},
                    {
                        'id': 'egg',
                        'name':'test_name_merge',
                        'type': 'foo_type',
                        'test_attr': ['a','b']
                    },
                    {
                        'id': 'equivalent_identifier_merge',
                        'equivalent_identifiers': ['TEST:00000'],
                        'merged_property': [
                            'a',
                            'b'
                        ]
                    }
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'CHEBI:28177', 'target_id': 'HGNC:2597'},
                    {
                        # Test if edges that are connected to merged nodes will be successfully merged with other duplicate edges
                        'source_id' : 'CHEBI:28177',
                        'target_id' : 'egg',
                        'type': ['merge_this'],
                        'merge_this_list' : ['edge_1'],
                        'unique_attr_e_1' : 'e_1',
                        'id' : 'winning_edge_id'
                    },
                ]
            },
            'knowledge_map': [
                {
                    'node_bindings': {
                        'chemical_substance': 'CHEBI:28177',
                        'gene': 'HGNC:2597'
                    },
                    'edge_bindings': {}
                }
            ]
        },
        {
            'knowledge_graph': {
                'nodes': [
                    {'id': 'CHEBI:28177', 'type': 'chemical_substance'},
                    {
                        'id': 'also_test_array_type_and_string_type_merge',
                        'name':'test_name_merge',
                        'type': ['foo_type','bar_type'],
                        'test_attr': ['a','c']
                    },
                    {'id': 'TEST:00000', 'type': 'test', 'merged_property': ['a','c']},
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'CHEBI:28177', 'target_id': 'TEST:00000'},
                    {
                        'source_id' : 'CHEBI:28177',
                        'target_id' : 'also_test_array_type_and_string_type_merge',
                        'type': ['merge_this'],
                        'merge_this_list' : ['edge_2'],
                        'unique_attr_e_2' : 'e_2'
                    }
                ]
            },
            'knowledge_map': [
                {
                    'node_bindings': {
                        'chemical_substance': 'CHEBI:28177',
                        'test': 'TEST:00000'
                    },
                    'edge_bindings': {}
                }
            ]
        }
    ]

    expected_result = {
        "knowledge_graph": {
            "edges": [
                {
                    "id": "e0",
                    "source_id": "CHEBI:28177",
                    "target_id": "HGNC:2597",
                    "type": []
                },
                {
                    "id": "e0",
                    "source_id": "CHEBI:28177",
                    "target_id": "equivalent_identifier_merge",
                    "type": []
                },
                {
                    "id" : "winning_edge_id",
                    "source_id" : "CHEBI:28177",
                    "target_id" : "egg",
                    "type" : ["merge_this"],
                    "merge_this_list" : ["edge_1", "edge_2"],
                    "unique_attr_e_1" : "e_1",
                    "unique_attr_e_2" : "e_2"
                }
            ],
            "nodes": [
                {
                    "equivalent_identifiers": [
                        "CHEBI:28177"
                    ],
                    "id": "CHEBI:28177",
                    "type": ["chemical_substance"]
                },
                {
                    "equivalent_identifiers": [
                        "HGNC:2597"
                    ],
                    "id": "HGNC:2597",
                    "type": ["gene"]
                },
                {
                    "equivalent_identifiers": [
                        "also_test_array_type_and_string_type_merge",
                        "egg"
                    ],
                    "type": [
                        "foo_type",
                        "bar_type"
                    ],
                    "id": "egg",
                    "name": "test_name_merge",
                    "test_attr": [
                        "a",
                        "b",
                        "c"
                    ]
                },
                {
                    "equivalent_identifiers": [
                        "TEST:00000",
                        "equivalent_identifier_merge"
                    ],
                    "merged_property": ["a", "b", "c"],
                    "id": "equivalent_identifier_merge",
                    "type": ["test"]
                }
            ]
        },
        "knowledge_map": [
            {
                "edge_bindings": {},
                "node_bindings": {
                    "chemical_substance": "CHEBI:28177",
                    "gene": "HGNC:2597"
                }
            },
            {
                "edge_bindings": {},
                "node_bindings": {
                    "chemical_substance": "CHEBI:28177",
                    "test": "equivalent_identifier_merge"
                }
            }
        ],
        'question_graph': {
            'edges': [
                {
                    'id': 'foo',
                    'type': 'test'
                }
            ],
            'nodes': [
                {
                    'id': 'bar',
                    'type': 'bartest'
                }
            ]
        }
    }
    merged_results = select.merge_results (
        mock_responses,
        tranql,
        {
            'edges': [
                {
                    'id': 'foo',
                    'type': 'test'
                }
            ],
            'nodes': [
                {
                    'id': 'bar',
                    'type': 'bartest'
                }
            ]
        },
        root_order=None
    )
    assert ordered(merged_results) == ordered(expected_result)
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
        assert sub_schema_plan[2][0][0].type_name == "disease"
        assert sub_schema_plan[2][0][0].name == "cohort_diagnosis"
        assert sub_schema_plan[2][0][0].nodes == ["MONDO:0004979"]

        assert sub_schema_plan[2][0][1].direction == "->"
        assert sub_schema_plan[2][0][1].predicate == None

        assert sub_schema_plan[2][0][2].type_name == "disease"
        assert sub_schema_plan[2][0][2].name == "diagnoses"
        assert sub_schema_plan[2][0][2].nodes == []
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

    assert len(statements) == 2

    for statement in statements:
        assert_lists_equal(
            list(statement.query.concepts.keys()),
            [
                "cohort_diagnosis",
                "diagnoses"
            ]
        )

        assert statement.query.concepts['cohort_diagnosis'].nodes == ["MONDO:0004979"]
        assert statement.query.concepts['diagnoses'].nodes == []
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
        questions = ast.statements[2].generate_questions (app)
        nodes = questions[0]['question_graph']['nodes']
        edges = questions[0]['question_graph']['edges']
        node_index = { n['id'] : i for i, n in enumerate (nodes) }
        assert nodes[-1]['curie'] == disease_id
        assert nodes[0]['curie'] == chemical
        assert node_index[edges[-1]['target_id']] == node_index[edges[-1]['source_id']] - 1

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
    #print (f"resolved variables --> {json.dumps(output, indent=2)}")
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
       SET '$.knowledge_graph.nodes.[*].id' AS chemical_exposures

    SELECT chemical_substance->gene->biological_process->anatomical_entity
      FROM "/graph/gamma/quick"
     WHERE chemical_substance = $chemical_exposures
       SET knowledge_graph
    """)

    #print (f"{ast}")
    expos = tranql.context.resolve_arg("$chemical_exposures")
    #print (f" expos =======> {json.dumps(expos)}")

    kg = tranql.context.resolve_arg("$knowledge_graph")
    assert kg['knowledge_graph']['nodes'][0]['id'] == "CHEBI:28177"
    assert kg['knowledge_map'][0]['node_bindings']['chemical_substance'] == "CHEBI:28177"


def test_unique_ids_for_repeated_concepts():
    tranql = TranQL()
    ast = tranql.parse(
        """
        SELECT g1:gene->g2:gene
        FROM '/schema'
        """
    )
    select_statement = ast.statements[0]
    question = select_statement.generate_questions(tranql)[0]
    import json
    print(
        json.dumps(
            question, indent=4
        )
    )
    assert question['question_graph']['nodes'] == [
        {
            'id': 'g1',
            'type': 'gene'
        },
        {
            'id': 'g2',
            'type': 'gene'
        }
    ]

def test_setting_values_for_repeated_concepts():
    tranql = TranQL()
    gene_list_1 = ['BRCA1', 'BRCA2']
    gene_list_2 = ['LTA', 'TNF']
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
    questions = ast.statements[2].generate_questions(tranql)
    question_nodes = reduce(lambda x, y: x + y,
                            map(lambda question: question['question_graph']['nodes'], questions),
                            [])
    question_edges = reduce(lambda x, y: x + y,
                            map(lambda question: question['question_graph']['edges'], questions),
                            [])
    curies = list(map(lambda node: node['curie'], question_nodes))
    for gene in gene_list_1:
        assert gene in curies
    for gene in gene_list_2:
        assert gene in curies

    # also test if direction is good
    for e in question_edges:
        print(e)
        assert e['source_id'] == 'g1'
        assert e['target_id'] == 'g2'

def test_schema_can_talk_to_automat():
    config_file = os.path.join(os.path.dirname(__file__),"..","conf","schema.yaml")
    with open(config_file) as stream:
        schema_yml = yaml.load(stream, Loader=yaml.Loader)
    automat_url = schema_yml['schema']['automat']['registry_url'].rstrip('/') # servers as a check too if we even load it
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
        schema_factory = SchemaFactory('http://localhost:8099', use_registry=False, create_new=True,  update_interval=1)
        schema = schema_factory.get_instance()
        assert len(schema.schema) == 0

def test_registry_enabled():
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
        schema_factory = SchemaFactory('http://localhost:8099', use_registry=True, update_interval=1, create_new=True)
        schema = schema_factory.get_instance()
        assert len(schema.schema) > 1


def test_registry_adapter_automat():
    from tranql.tranql_schema import RegistryAdapter

    # let pretend automat url is automat and we will mask what we expect to be called
    # since there is no real logic here we just have to make sure apis are called

    with requests_mock.mock() as mock_server:
        mock_server.get('http://automat/registry', json=['kp1'])
        expected_response = ['lets pretend this was a schema']
        mock_server.get('http://automat/kp1/graph/schema', json=expected_response)
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
                'registry_url': 'https://automat.renci.org',
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
        schema_factory = SchemaFactory(
            backplane='http://localhost:8091',
            use_registry=True,
            update_interval=update_interval,
            create_new=True
        )
        with requests_mock.mock() as m:
            # setup mock kps
            kps = ['kp1', 'kp2']
            for kp in kps:
                m.get(f'https://automat.renci.org/{kp}/graph/schema', json=mock_schema_response[kp])
            # say registry returns kp1 on first call
            m.get('https://automat.renci.org/registry', json=['kp1'])
            # here some Tranql objects have this instance.
            schema1 = schema_factory.get_instance()
            schema2 = schema_factory.get_instance()
            # Doing something on second  schema instance should not affect the first.
            schema2.schema['Lets add something'] = {'add some thing': 'dsds'}
            assert 'Lets add something' not in schema1.schema

        with requests_mock.mock() as m:
            # setup mock kps
            kps = ['kp1', 'kp2']
            for kp in kps:
                m.get(f'https://automat.renci.org/{kp}/graph/schema', json=mock_schema_response[kp])
            # Now we change what registry returns and wait for update
            m.get('https://automat.renci.org/registry', json=['kp2'])
            # lets wait for next updated and request a new object
            # testing to see if our new request results will affect the
            # the original schema
            time.sleep(update_interval + 1) # sleeping to ensure update thread is working
            schema2 = schema_factory.get_instance()
            # original reference to Schema should be different from second.
            assert schema1 != schema2
