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
#       graph analytics, machine learning, and statistical methods.
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
import traceback
from tranql.config import Config
from tranql.util import Context
from tranql.util import JSONKit
from tranql.util import Concept
from tranql.util import LoggingUtil
from tranql.tranql_ast import TranQL_AST
from pyparsing import (
    Combine, Word, White, Literal, delimitedList, Optional,
    Group, alphas, alphanums, printables, Forward, oneOf, quotedString,
    ZeroOrMore, restOfLine, CaselessKeyword, ParserElement, LineEnd,
    removeQuotes, pyparsing_common as ppc)

LoggingUtil.setup_logging ()
logger = logging.getLogger (__name__)

"""
A program is a list of statements.
Statements can be 'set' or 'select' statements.

"""
statement = Forward()
SELECT, FROM, WHERE, SET, AS, CREATE, GRAPH, AT = map(
    CaselessKeyword,
    "select from where set as create graph at".split())

concept_name    = Word( alphas, alphanums + ":_")
ident          = Word( "$" + alphas, alphanums + "_$" ).setName("identifier")
columnName     = delimitedList(ident, ".", combine=True).setName("column name")
columnNameList = Group( delimitedList(columnName))
tableName      = delimitedList(ident, ".", combine=True).setName("column name")
tableName      = quotedString.setName ("service name")
tableNameList  = Group(delimitedList(tableName))

SEMI,COLON,LPAR,RPAR,LBRACE,RBRACE,LBRACK,RBRACK,DOT,COMMA,EQ = map(Literal,";:(){}[].,=")
arrow = Literal ("->") | \
        Literal ("<-") | \
        Group(Literal("-[") + concept_name + Literal("]->")) | \
        Group(Literal("<-[") + concept_name + Literal("]-"))
question_graph_element = (
    concept_name + ZeroOrMore ( LineEnd () )
) | \
Group (
    concept_name + COLON + concept_name + ZeroOrMore ( LineEnd () )
)
question_graph_expression = question_graph_element + ZeroOrMore(arrow + question_graph_element)

whereExpression = Forward()
and_, or_, in_ = map(CaselessKeyword, "and or in".split())

binop = oneOf("= != =~ !=~ < > >= <= eq ne lt le gt ge", caseless=True)
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
        Group(SELECT + question_graph_expression)("concepts") + optWhite +
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
    def __init__(self, backplane):
        self.program = program_grammar
        self.backplane = backplane
    def parse (self, line):
        """ Parse a program, returning an abstract syntax tree. """
        result = self.program.parseString (line)
        return TranQL_AST (result.asList (), self.backplane)

class TranQL:
    """
    Define the language interpreter.
    It provides an interface to
      Execute the parser
      Generate an abstract syntax tree
      Execute statements in the abstract syntax tree.
    """
    def __init__(self, backplane="http://localhost:8099", asynchronous=True):
        """ Initialize the interpreter. """
        self.context = Context ()
        config_path = "conf.yml"
        self.config = Config (config_path)

        t = os.path.join (os.path.dirname (__file__), "conf.test")
        with open(t, "w") as stream:
            stream.write (f" --- backplane: {self.config['BACKPLANE']}")

        env_backplane = self.config['BACKPLANE']
        if env_backplane:
            backplane = env_backplane
        self.context.set ("backplane", backplane)
        self.parser = TranQLParser (backplane)

        self.asynchronous = asynchronous

    def parse (self, program):
        """ If we just want the AST. """
        return self.parser.parse (program)

    def parse_file (self, file_name):
        result = None
        with open(file_name, "r") as stream:
            result = self.parse (stream.read ())
        return result

    def execute (self, program, cache=False):
        """ Execute a program - a list of statements. """
        ast = None
        if cache:
            requests_cache.install_cache('demo_cache',
                                         allowable_methods=('GET', 'POST', ))
        else:
            requests_cache.disabled()

        if isinstance(program, str):
            ast = self.parse (program)
        if not ast:
            raise ValueError (f"Unhandled type: {type(program)}")
        for statement in ast.statements:
            logger.debug (f"execute: {statement} type={type(statement).__name__}")
            statement.execute (interpreter=self)
        return self.context

    def execute_file (self, program):
        """ Execute a file on disk, soup to nuts. """
        with open (program, "r") as stream:
            self.execute (stream.read ())
        return self.context

    def __call__(self, val):
        self.execute (val)

    def show (self, type_name, k='result', n=10, start=0):
        self.context.toph (type_name=type_name, k=k, n=n, start=start)

    def val (self, term):
        result = {}
        if isinstance(term, list):
            for t in term:
                result.update ({ x : self.context.mem[x] for x in list(self.context.mem.keys ()) if x.lower().startswith (t) })
        else:
            result = { x : self.context.mem[x] for x in list(self.context.mem.keys ()) if x.lower().startswith (term) }
        return result

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
                        if block.strip() == 'quit':
                            break
                        else:
                            #print (f"---> {block}")
                            if not '\n' in block.strip():
                                if block.startswith('$'):
                                    val = self.context.resolve_arg (block.strip())
                                    print (f"{val}")
                            else:
                                response = self.execute (block)
                                print (f"{json.dumps(response.mem, indent=2)}")
                    print (f"$ ", end='')
                else:
                    buf.append (line)
            except Exception as e:
                print (e)
                traceback.print_exc ()
                print (str(e))
        return self.context

def set_verbose ():
    """ Turn up logging. """
    logging.getLogger().setLevel (logging.DEBUG)
    for logger_name in [ "tranql.main", "tranql.tranql_ast", "tranql.util" ]:
        logger = logging.getLogger (logger_name)
        logger.setLevel (logging.DEBUG)

def main ():
    """ Process arguments. """
    arg_parser = argparse.ArgumentParser(
        description='TranQL',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog,
                                                            max_help_position=180))
    arg_parser.add_argument('-v', '--verbose', help="Verbose mode.", action="store_true")
    arg_parser.add_argument('-c', '--cache',
                            help="Cache responses from backplane services?",
                            action="store_true")
    arg_parser.add_argument('-b', '--backplane',
                            help="Backplane URL prefix",
                            default="http://localhost:8099")
    arg_parser.add_argument('-i', '--shell',
                            help="The interpreter read-eval-print-loop (REPL).",
                            action="store_true")
    arg_parser.add_argument('-s', '--source', help="The program's source file")
    arg_parser.add_argument('-o', '--output', help="Output destination")
    arg_parser.add_argument('-a', '--arg', help="Output destination",
                            action="append", default=[])
    # -x is placeholder as '-a' taken; should eventually replace with better fitting letter
    arg_parser.add_argument('-x', '--asynchronous', default=False, help="Run requests asynchronously with asyncio")
    args = arg_parser.parse_args ()

    global logger
    """ Parse command line arguments to the query. """
    query_args = { k : v for k, v in [ arg.split("=") for arg in args.arg ] }

    if args.verbose:
        set_verbose ()

    if args.cache:
        """ Turn on the requests cache. """
        requests_cache.install_cache('demo_cache',
                                     allowable_methods=('GET', 'POST', ))

    """ Create an interpreter. """
    tranql = TranQL (backplane = args.backplane, asynchronous = args.asynchronous)
    for k, v in query_args.items ():
        logger.debug (f"setting {k}={v}")
        tranql.context.set (k, v)
    context = None
    if args.shell:
        """ Run it interactively. """
        context = tranql.shell ()
    elif args.source:
        """ Run a program. """
        context = tranql.execute_file (args.source)
        if args.output == 'stdout':
            print (f"{json.dumps(context.mem, indent=2)}")
            print (f"top-gene: {json.dumps(context.top('gene',k='chemical_pathways'), indent=2)}")
    else:
        print ("Either source or shell must be specified")

if __name__ == '__main__':
    main ()
