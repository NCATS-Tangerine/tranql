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
from tranql.tranql_ast import SetStatement, SelectStatement
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.tests.mocks import MockHelper
from tranql.tests.mocks import MockMap
from tranql.tranql_schema import SchemaFactory
import requests_mock
from unittest.mock import patch
import copy, time
from tranql.utils.merge_utils import connect_knowledge_maps, find_all_paths

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
            'question_order' : ['chemical_substance','disease'],
            'question_graph': {
                'nodes': [
                    {'id': 'chemical_substance', 'type': 'chemical_substance'},
                    {'id': 'disease', 'type': 'disease'}
                ],
                'edges':[
                    {'id': 'e0', 'source_id': 'chemical_substance', 'target_id': 'disease'}
                ]
            }
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
            'question_order' : ['disease','gene','metabolite'],
            'question_graph' : {
                'nodes': [
                    {'id': 'disease', 'type':'disease'},
                    {'id': 'gene', 'type':'gene'},
                    {'id': 'metabolite', 'type': 'metabolite'}
                ],
                'edges': [
                    {'id': 'e0', 'source_id':'disease', 'target_id':'gene'},
                    {'id': 'e1', 'source_id': 'gene', 'target_id': 'metabolite'}
                ]
            }
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
            'question_order' : ['disease','gene','metabolite'],
            'question_graph' : {
                'nodes': [
                    {'id': 'disease', 'type':'disease'},
                    {'id': 'gene', 'type':'gene'},
                    {'id': 'metabolite', 'type': 'metabolite'}
                ],
                'edges': [
                    {'id': 'e0', 'source_id':'disease', 'target_id':'gene'},
                    {'id': 'e1', 'source_id': 'gene', 'target_id': 'metabolite'}
                ]
            }
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
            'question_order' : ['metabolite','protein'],
            'question_graph': {
                'nodes': [
                    {'id': 'metabolite', 'type': 'metabolite'},
                    {'id': 'protein', 'type': 'protein'}
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'metabolite', 'target_id': 'protein'}
                ]
            }
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
            'question_order' : ['metabolite','protein'],
            'question_graph': {
                'nodes': [
                    {'id': 'metabolite', 'type': 'metabolite'},
                    {'id': 'protein', 'type': 'protein'}
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'metabolite', 'target_id': 'protein'}
                ]
            }
        }
    ]

    merged = SelectStatement.connect_knowledge_maps(responses,[
        'chemical_substance',
        'disease',
        'gene',
        'metabolite',
        'protein'
    ])
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
                "chemical_substance" : ["CHEBI:100"],
                "disease" : ["MONDO:50"],
            },
            "edge_bindings" : {
                "e0" : "ROOT_EDGE"
            },
            "score": 0
        },
        {
            "node_bindings" : {
                "gene" : ["HGNC:1"],
                "metabolite" : ["KEGG:C00017"]
            },
            "edge_bindings" : {
                "e1" : "TEST_EDGE",
            },
            "score": 0
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

    question_graph = {
            'edges': [
                {
                    'id': 'foo',
                    'type': 'test',
                    'source_id': 'chemical_substance',
                    'target_id': 'gene'
                }, {
                    'id': 'edge_2',
                    'type': 'other_type',
                    'source_id': 'chemical_substance',
                    'target_id': 'test'
                }
            ],
            'nodes': [
                {
                    'id': 'chemical_substance',
                    'type': 'chemical_substance',
                }, {
                    'id': 'gene',
                    'type': 'gene'
                }, {
                    'id': 'test',
                    'type': 'test'
                }
            ]
        }

    select = ast.statements[0]

    # What is the proper format for the name of a mock file? This should be made into one
    mock_responses = [
        {
            'question_graph': question_graph,
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
            'question_graph': question_graph,
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
                        'unique_attr_e_2' : 'e_2',
                        'id': 'other_edge_id'
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
            # no edge bindings exist in response so we should expect nothing here
        ],
        'question_graph': question_graph
    }
    merged_results = select.merge_results (
        mock_responses,
        tranql,
        question_graph,
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
    assert kg['knowledge_map'][0]['node_bindings']['chemical_substance'] == ["CHEBI:28177"]


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
        'nodes': [
            {'id': 'n1', 'type': 'tp1'},
            {'id': 'n2', 'type': 'tp2'},
        ],
        'edges': [
            {'id': 'e1', 'source_id': 'n1', 'target_id': 'n2'},
        ]
    }
    k_graph = {
        'nodes': [{
            'id': 'some:curie',
            'type': ['tp1'],
            'name': 'first node'
        },{
            'id': 'some:curie2',
            'type': ['tp2'],
            'name': 'second node'
        }],
        'edges': [
            {'id': 'e1-kg-id'},
            {'id': 'e2-kg-id'}
        ]
    }
    k_map = [
        {
            'node_bindings': {
                # q_graph id : kg_graph id
                'n1': 'some:curie',
                'n2': 'some:curie2'
            },
            'edge_bindings': {
                'e1': 'e1-kg-id'
            }
        }
    ]
    full_response = {
        'knowledge_graph': k_graph,
        'question_graph': q_graph,
        'knowledge_map': k_map
    }
    merged_k_map = connect_knowledge_maps([full_response],[])
    assert len(merged_k_map) == len(k_map)
    assert merged_k_map[0]['node_bindings'] == k_map[0]['node_bindings']
    assert merged_k_map[0]['edge_bindings'] == k_map[0]['edge_bindings']

def test_merge_two_responses_connected_one_after_the_other():
    q_G_1 = {
        'nodes': [{'id': 'n0'}, {'id': 'n1'}],
        'edges': [{'id': 'e1', 'source_id': 'n0', 'target_id': 'n1'}]
    }
    q_G_2 = {
        'nodes': [{'id': 'n1'}, {'id': 'n2'}],
        'edges': [{'id': 'e1-1', 'source_id': 'n1', 'target_id': 'n2'}]
    }
    k_map_1 = [
        {
            'node_bindings': {'n0': 'kg_id_of_n0', 'n1': 'kg_id_of_n1'},
            'edge_bindings': {'e1': 'kg_id_of_e1'}}
    ]
    k_map_2 = [
        {
            'node_bindings': {'n1': 'kg_id_of_n1', 'n2': 'kg_id_of_n1'},
            'edge_bindings': {'e1-1': 'kg_id_of_e1-1'}
        }
    ]
    response = connect_knowledge_maps([{
        'question_graph': q_G_1,
        'knowledge_map': k_map_1,
    }, {
        'question_graph': q_G_2,
        'knowledge_map': k_map_2
    }], [])
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
        'nodes': [{'id': 'n0'}, {'id': 'n1'}],
        'edges': [{'id': 'e1', 'source_id': 'n0', 'target_id': 'n1'}]
    }
    q_G_2 = {
        'nodes': [{'id': 'n1'}, {'id': 'n2'}],
        'edges': [{'id': 'e1-1', 'source_id': 'n1', 'target_id': 'n2'}]
    }
    k_map_1 = [
        {
            'node_bindings': {'n0': 'kg_id_of_n0', 'n1': 'kg_id_of_n1'},
            'edge_bindings': {'e1': 'kg_id_of_e1'}
        }
    ]
    k_map_2 = [
        {
            'node_bindings': {'n1': 'HEREISWHEREDISCONNECTIONIS', 'n2': 'kg_id_of_n1'},
            'edge_bindings': {'e1-1': 'kg_id_of_e1-1'}
        }
    ]
    response = connect_knowledge_maps([{
        'question_graph': q_G_1,
        'knowledge_map': k_map_1,
    }, {
        'question_graph': q_G_2,
        'knowledge_map': k_map_2
    }], [])
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
        'nodes': [
            {'id': 'A', 'type': 'A'},
            {'id': 'B', 'type': 'B'},
            {'id': 'C', 'type': 'C'},
            {'id': 'D', 'type': 'D'},
            {'id': 'E', 'type': 'E'}
        ], 'edges': [
            {'id': 'e-A-B', 'source_id': 'A', 'target_id':'B'},
            {'id': 'e-B-C', 'source_id': 'B', 'target_id': 'C'},
            {'id': 'e-C-D', 'source_id': 'C', 'target_id': 'D'},
            {'id': 'e-D-E', 'source_id': 'D', 'target_id': 'E'}
        ]
    }
    q_g_2 = {
        'nodes': [
            {'id': 'B', 'type': 'B'},
            {'id': 'C', 'type': 'C'},
            {'id': 'G', 'type': 'G'},
            {'id': 'D', 'type': 'D'}
        ],
        'edges': [
            {'id': 'e-B-C', 'source_id': 'B', 'target_id': 'C'},
            {'id': 'e-C-G', 'source_id': 'C', 'target_id': 'G'},
            {'id': 'e-G-D', 'source_id': 'G', 'target_id': 'D'}
        ]
    }
    q_g_3 = {
        'nodes': [
            {'id': 'A', 'type': 'A'},
            {'id': 'B', 'type': 'B'}
        ],
        'edges': [
            {'id': 'e-A-B', 'source_id': 'A', 'target_id': 'B'}
        ]
    }
    q_g_4 = {
        'nodes': [
            {'id': 'A', 'type': 'A'},
            {'id': 'B', 'type': 'B'}
        ],
        'edges': [
            {'id': 'e-A-B', 'source_id':'A', 'target_id': 'B'}
        ]
    }

    # Lets make some graphs that look like the above ones

    k_map_1 = [
        {
            'node_bindings': {
                'A': 'a',
                'B': 'b',
                'C': 'c',
                'D': 'd',
                'E': 'e'
            },
            'edge_bindings': {
                'e-A-B': 'e-a-b',
                'e-B-C': 'e-b-c',
                'e-C-D': 'e-c-d',
                'e-D-E': 'e-d-e'
            }
        },
    ]    # a - b - c - d -e
    k_map_2 = [{
        'node_bindings': {
            'B': 'b',
            'C': 'f',
            'G': 'g',
            'D': 'd'
        },
        'edge_bindings': {
            'e-B-C': 'e-b-f',
            'e-C-G': 'e-c-g',
            'e-G-D': 'e-g-d'
        }
    }]  # b - f -  g - d
    k_map_3 = [{
        'node_bindings': {
            'A': 'a1',
            'B': 'b1'
        },
        'edge_bindings': {
            'e-A-B': 'e-a1-b1'
        }
    }]
    k_map_4 = [
        {'node_bindings': {
            'A': 'a2',
            'B': 'b'
        }, 'edge_bindings': {
            'e-A-B': 'e-a2-b'
        }
        }
    ]
    responses = [
        {'question_graph': q_g_1, 'knowledge_map': k_map_1},
        {'question_graph': q_g_2, 'knowledge_map': k_map_2},
        {'question_graph': q_g_3, 'knowledge_map': k_map_3},
        {'question_graph': q_g_4, 'knowledge_map': k_map_4}
    ]
    merged_paths = connect_knowledge_maps(responses, [])
    assert len(merged_paths) == 5
    # check path a->b->c->d->e
    p1 = {
        'node_bindings': {
        'A':['a'],
        'B':['b'],
        'C':['c'],
        'D':['d'],
        'E':['e']
    }, 'edge_bindings':{
         'e-A-B': 'e-a-b',
         'e-B-C': 'e-b-c',
         'e-C-D': 'e-c-d',
         'e-D-E': 'e-d-e'
        },
        'score': 0
    }
    assert p1 in merged_paths
    p2 = {
        'node_bindings': {
        #   Query_graph_id , Knowledge_graph_id
            'A': ['a'],
            'B': ['b'],
            'C': ['f'],
            'G': ['g'],
            'D': ['d'],
            'E': ['e']
        }, 'edge_bindings': {
            'e-A-B': 'e-a-b',
            'e-B-C': 'e-b-f',
            'e-C-G': 'e-c-g',
            'e-G-D': 'e-g-d',
            'e-D-E': 'e-d-e'
        },
        'score': 0
    }
    # check path p2: a:A->b:B->f:C->g:G->d:D->e:E
    assert p2 in merged_paths
    # Check for p3
    # p3: a1->b1
    p3 = {
        'node_bindings': {
            'A': ['a1'],
            'B': ['b1']
        },
        'edge_bindings': {
            'e-A-B': 'e-a1-b1'
        },
        'score': 0
    }
    assert  p3 in merged_paths

    # check p4
    # p4: a2->b->c->d->e
    p4 = {
        'node_bindings': {
            'A': ['a2'],
            'B': ['b'],
            'C': ['c'],
            'D': ['d'],
            'E': ['e']
        },
        'edge_bindings': {
            'e-A-B': 'e-a2-b',
            'e-B-C': 'e-b-c',
            'e-C-D': 'e-c-d',
            'e-D-E': 'e-d-e'
        }, 'score': 0
    }
    assert  p4 in merged_paths
    # check p5
    # p5: a2->b->f->g - d->e
    p5 = {
        'node_bindings': {
            'A': ['a2'],
            'B': ['b'],
            'C': ['f'],
            'D': ['d'],
            'E': ['e'],
            'G': ['g']
        }, 'edge_bindings': {
            'e-A-B': 'e-a2-b',
            'e-B-C': 'e-b-f',
            'e-C-G': 'e-c-g',
            'e-G-D': 'e-g-d',
            'e-D-E': 'e-d-e'
        }, 'score': 0
    }
    assert p5 in merged_paths


def test_merge_preserves_edge_ids():
    kg = {
        'question_graph': {
            'nodes': [
                {'id': 'n0', 'type': 'type1', 'curie': 'CURIE:1'},
                {'id': 'n1', 'type': 'type2'}
            ],
            'edges': [
                {'id': 'e0', 'source_id': 'n0', 'target_id': 'n1'}
            ]
        },
        'knowledge_graph': {
            'nodes': [
                {'id': 'CURIE:1', 'name': 'Node 1'},
                {'id': 'curie:2', 'name': 'another node'},
                {'id': 'curie:3', 'name': 'third node'}
            ],
            'edges': [
                {'id': 'curie1:curie2', 'type': 'related_to', 'source_id': 'CURIE:1', 'target_id': 'curie:2'},
                {'id': 'curie1:curie2Duplicate', 'type': 'related_to', 'source_id': 'CURIE:1', 'target_id': 'curie:2'},
                {'id': 'curie1:curie3', 'type': 'related_to', 'source_id': 'CURIE:1', 'target_id': 'curie:3'}
            ]
        },
        'knowledge_map': [
            {
                'node_bindings': {
                    'n0': 'CURIE:1',
                    'n1': 'curie:2'
                }, 'edge_bindings': {
                'e0': ['curie1:curie2']
            }
            }, {
                'node_bindings': {
                    'n0': 'CURIE:1',
                    'n1': 'curie:2'
                }, 'edge_bindings': {
                    'e0': ['curie1:curie2Duplicate']
                }
            }, {
                'node_bindings': {
                    'n0': 'CURIE:1',
                    'n1': 'curie:3'
                }, 'edge_bindings': {
                    'e0': ['curie1:curie3']
                }
            }
        ]
    }
    tranql = TranQL()
    responses = [kg]
    select_statement = SelectStatement(tranql)
    result = select_statement.merge_results(
        responses, tranql, responses[0]['question_graph'])
    edges = result['knowledge_graph']['edges']
    all_edge_ids = set(e["id"] for e in edges)
    for answer_binding in result['knowledge_map']:
        e_b = answer_binding['edge_bindings']
        edge_ids = reduce(lambda x, y : x + y, map(lambda x: e_b[x], e_b), [])
        for i in edge_ids:
            assert i in all_edge_ids, print(edge_ids)

def test_merge_should_preserve_score():
    """
    Once  a knowledge response is merged
    :return:
    """
    query_graph = {
        'nodes': [
            {'id': 'A', 'type': 'A'},
            {'id': 'B', 'type': 'B'}
        ], 'edges': [
            {'id': 'e-A-B', 'source_id': 'A', 'target_id':'B'}
        ]
    }
    knowledge_graph = {
        'nodes': [
            {'id': 'KG_ID_A', 'name': 'node A from kg'},
            {'id': 'KG_ID_B', 'name': 'node B from kg'},
            {'id': 'KG_ID_AA', 'name': 'node AA from kg'},
            {'id': 'KG_ID_BB', 'name': 'node BB from kg'},
                  ],
        'edges': [
            {'id': 'KG_ID_A_B', 'type': 'related_to', 'source_id': 'KG_ID_A', 'target_id': 'KG_ID_B'},
            {'id': 'KG_ID_AA_BB', 'type': 'related_to', 'source_id': 'KG_ID_AA', 'target_id': 'KG_ID_BB'},
        ]
    }
    knowledge_map = [
        {
            'node_bindings': {'A': ['KG_ID_A'],'B': ['KG_ID_B']},
            'edge_bindings': {'e-A-B': ['KG_ID_A_B']},
            'score': 1
        },
        {
            'node_bindings': {'A': ['KG_ID_AA'], 'B': ['KG_ID_BB']},
            'edge_bindings': {'e-A-B': ['KG_ID_AA_BB']},
            'score': 2
        }
    ]
    tranql = TranQL()
    responses = [{
        'question_graph': query_graph,
        'knowledge_map': knowledge_map,
        'knowledge_graph': knowledge_graph
    }]
    select_statement = SelectStatement(tranql)
    result = select_statement.merge_results(responses, tranql, query_graph, ['A','B'])
    for answer in result['knowledge_map']:
        assert 'score' in answer
        assert answer['score'] == 1 or answer['score'] == 2