# TranQL.py
#
#    TranQL is a query language for heterogenous federated knowledge sources.
#
#    The NCATS Data Translator program investigates the creation
#    of a data and computational engine to accelerate biomedical
#    insight.
#
#    It aims to do this through the design and large scale computational
#    interrelation of complex, heterogeneous biomedical knowledge.
#
#    Knowledge Sources
#
#       Knowledge sources provide semantically annotated graphs. In general,
#       nodes in the knowledge graph refer to entities defined in curated
#       ontologies.
#
#    Aggregators
#
#       A variety of processes exist for asking questions that span knowledge
#       sources, returning a knowledge graph referencing objects from disparate ontologies.
#
#    Reasoners
#
#       Reasoners apply analytics to knowledge graphs comprised of data from
#       multiple sources which, in addition to ontologies, will incorporate
#       graph analytics, machine learning, and statistical methods as needed.
#
#    TranQL borrows metaphors from both graph and relational query languages like
#    Cypher and SQL. We need both kinds of capabilities to address the range of
#    available data sets.

import argparse
import json
import logging
import os
import requests_cache
import sys
from tranql.util import Context
from tranql.util import JSONKit
from tranql.util import Concept
from tranql.util import LoggingUtil
from tranql.ast import TranQL_AST
from pyparsing import (
    Combine, Word, White, Literal, delimitedList, Optional,
    Group, alphas, alphanums, printables, Forward, oneOf, quotedString,
    ZeroOrMore, restOfLine, CaselessKeyword, ParserElement, LineEnd,
    removeQuotes, pyparsing_common as ppc)

LoggingUtil.setup_logging (
    default_path=os.path.join(os.path.dirname(__file__), 'logging.yaml'))

logger = logging.getLogger (__name__)

"""
A program is a list of statements.
Statements can be 'set' or 'select' statements.        
"""
statement = Forward()
SELECT, FROM, WHERE, SET, AS, CREATE, GRAPH, AT = map(
    CaselessKeyword,
    "select from where set as create graph at".split())

ident          = Word( "$" + alphas, alphanums + "_$" ).setName("identifier")
columnName     = delimitedList(ident, ".", combine=True).setName("column name")
columnNameList = Group( delimitedList(columnName))
tableName      = delimitedList(ident, ".", combine=True).setName("column name")
tableName      = quotedString.setName ("service name")
tableNameList  = Group(delimitedList(tableName))

SEMI,COLON,LPAR,RPAR,LBRACE,RBRACE,LBRACK,RBRACK,DOT,COMMA,EQ = map(Literal,";:(){}[].,=")
arrow = Literal ("->")
t_expr = Group(ident + LPAR + Word("$" + alphas, alphanums + "_$") + RPAR + ZeroOrMore(LineEnd())).setName("t_expr") | \
         Word(alphas, alphanums + "_$") + ZeroOrMore(LineEnd())
t_expr_chain = t_expr + ZeroOrMore(arrow + t_expr)

whereExpression = Forward()
and_, or_, in_ = map(CaselessKeyword, "and or in".split())

binop = oneOf("= != < > >= <= eq ne lt le gt ge", caseless=True)
realNum = ppc.real()
intNum = ppc.signed_integer()

# need to add support for alg expressions
columnRval = realNum | intNum | quotedString.addParseAction(removeQuotes) | columnName 
whereCondition = Group(
    ( columnName + binop + (columnRval | Word(printables) ) ) |
    ( columnName + in_ + "(" + delimitedList( columnRval ) + ")" ) |
    ( columnName + in_ + "(" + statement + ")" ) |
    ( "(" + whereExpression + ")" )
)
whereExpression << whereCondition + ZeroOrMore( ( and_ | or_ ) + whereExpression )

''' Assignment for handoff. '''
setExpression = Forward ()
setStatement = Group(
    ( ident ) |
    ( quotedString("json_path") + AS + ident("name") ) |
    ( "(" + setExpression + ")" )
)
setExpression << setStatement + ZeroOrMore( ( and_ | or_ ) + setExpression )

optWhite = ZeroOrMore(LineEnd() | White())

""" Define the statement grammar. """
statement <<= (
    Group(
        Group(SELECT + t_expr_chain)("concepts") + optWhite + 
        Group(FROM + tableNameList) + optWhite + 
        Group(Optional(WHERE + whereExpression("where"), "")) + optWhite + 
        Group(Optional(SET + setExpression("set"), ""))("select")
    )
    |
    Group(
        SET + (columnName + EQ + ( quotedString |
                                   ident |
                                   intNum |
                                   realNum ))
    )("set")
    |
    Group(
        #CREATE GRAPH $phenotypic_relationships AT $ndex AS "wf5_pheno_features"
        Group(CREATE + GRAPH + ident) + optWhite +
        Group(AT + ( ident | quotedString )) + optWhite +
        Group(AS + ( ident | quotedString ))
    )
)("statement")

""" Make a program a series of statements. """
program_grammar = statement + ZeroOrMore(statement)

""" Make rest-of-line comments. """
comment = "--" + restOfLine
program_grammar.ignore (comment)
        
class TranQLParser:
    """ Defines the language's grammar. """
    def __init__(self):
        self.program = program_grammar
    def parse (self, line):
        """ Parse a program, returning an abstract syntax tree. """
        result = self.program.parseString (line)
        return TranQL_AST (result.asList ())
        
class TranQL:
    """
    Define the language interpreter. 
    It provides an interface to
      Execute the parser
      Generate an abstract syntax tree
      Execute statements in the abstract syntax tree.
    """
    def __init__(self, backplane="http://localhost:8099"):
        """ Initialize the interpreter. """
        self.parser = TranQLParser ()
        self.context = Context ()
        self.context.set ("backplane", backplane)

    def execute_file (self, program):
        with open (program, "r") as stream:
            self.execute (stream.read ())
        return self.context
    
    def execute (self, program):
        """ Execute a program - a list of statements. """
        ast = None
        if isinstance(program, str):
            ast = self.parser.parse (program)
        if not ast:
            raise ValueError (f"Unhandled type: {type(program)}")
        for statement in ast.statements:
            print (f"{statement}")
            logger.info (f"{statement} {type(statement).__name__}")
            statement.execute (interpreter=self)
        return self.context

    def shell (self):
        """ Read, Eval, Print Loop. """
        header = """
  ______                 ____    __ 
 /_  __/________ _____  / __ \  / / 
  / / / ___/ __ `/ __ \/ / / / / /  
 / / / /  / /_/ / / / / /_/ / / /___
/_/ /_/   \__,_/_/ /_/\___\_\/_____/
                                     v0.1"""
        print (header)
        buf = []
        print (f"$ ", end='')
        while True:
            try:
                sys.stdout.flush ()
                line = sys.stdin.readline ()
                if line.isspace():
                    block = "".join (buf)
                    buf.clear ()
                    if len(block) > 0:
                        if block.strip() == 'quit()':
                            break
                        else:
                            self.execute (block)
                    print (f"$ ", end='')
                else:
                    buf.append (line)
            except Exception as e:
                print (e)
                print (str(e))
        return self.context
            
                
            
if __name__ == '__main__':
    
    """ Process arguments. """
    arg_parser = argparse.ArgumentParser(
        description='TranQL',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog,
                                                            max_help_position=180))
    arg_parser.add_argument('-d', '--verbose', help="Verbose mode.", action="store_true")
    arg_parser.add_argument('-c', '--cache', help="Cache.", action="store_true")
    arg_parser.add_argument('-b', '--backplane', help="Backplane URL prefix", default="http://localhost:8099")
    arg_parser.add_argument('-i', '--shell', help="The interpreter read-eval-print-loop (REPL).", action="store_true")
    arg_parser.add_argument('-s', '--source', help="The program's source file")
    args = arg_parser.parse_args ()


    #numeric_level = getattr(logging, loglevel.upper(), None)
    #if not isinstance(numeric_level, int):
    #    raise ValueError('Invalid log level: %s' % loglevel)
    #logging.basicConfig(level=logging.DEBUG)

    if args.cache:
        requests_cache.install_cache('demo_cache',
                                     allowable_methods=('GET', 'POST', ))

    tranql = TranQL (backplane = args.backplane)
    context = None
    if args.shell:
        context = tranql.shell ()
    else:
        context = tranql.execute_file (args.source)
    
