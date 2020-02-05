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
from tranql.grammar import program_grammar, incomplete_program_grammar
from pyparsing import ParseException
from tranql.exception import TranQLException

LoggingUtil.setup_logging ()
logger = logging.getLogger (__name__)

class Parser:
    def __init__(self, grammar, backplane):
        self.program = grammar
        self.backplane = backplane

    def tokenize (self, line):
        return self.program.parseString (line)

    def parse (self, line):
        """ Parse a program, returning an abstract syntax tree. """
        try:
            result = self.tokenize (line)
        except ParseException as pEx:
            message = f"Parsing error at line {pEx.lineno}, col {pEx.col}."
            details = f'{pEx.line}'
            details += f"\n{' ' * (pEx.col -1)}^^^"
            details += f"\n{pEx.msg}"
            logger.error(message + '\n' + details)
            raise TranQLException(message, details)

        return TranQL_AST (result.asList (), self.backplane)

class TranQLParser(Parser):
    """ Defines the language's grammar. """
    def __init__(self, backplane):
        super().__init__ (program_grammar, backplane)

class TranQLIncompleteParser(Parser):
    def __init__(self, backplane):
        super().__init__ (incomplete_program_grammar, backplane)

class TranQL:
    """
    Define the language interpreter.
    It provides an interface to
      Execute the parser
      Generate an abstract syntax tree
      Execute statements in the abstract syntax tree.
    """
    def __init__(self, backplane="http://localhost:8099", options={}):
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

        # Priority:
        #   1 - Options
        #   2 - Config
        #   3 - Default

        self.asynchronous = options.get("asynchronous", self.config.get('ASYNCHRONOUS_REQUESTS', True))
        self.name_based_merging = options.get("name_based_merging", self.config.get('NAME_BASED_MERGING', True))
        self.resolve_names = options.get("resolve_names", self.config.get('RESOLVE_NAMES', False))
        self.dynamic_id_resolution = options.get("dynamic_id_resolution", self.config.get('DYNAMIC_ID_RESOLUTION', False))

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
    # -x is placeholder as '-a' taken; should eventually replace with a more fitting letter
    arg_parser.add_argument('-x', '--asynchronous', default=True, help="Run requests asynchronously resulting in faster queries")
    arg_parser.add_argument('-n', '--name_based_merging', default=True, help="Merge nodes that have the same name properties as one another")
    arg_parser.add_argument('-r', '--resolve_names', default=False, help="(Experimental) Resolve equivalent identifiers of nodes in responses via the Bionames API. Can result in a more thoroughly merged graph.")
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
    options = {x: vars(args)[x] for x in vars(args) if x in ["asynchronous","name_based_merging","resolve_names","dynamic_id_resolution"]}
    tranql = TranQL (backplane = args.backplane, options = options)
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
