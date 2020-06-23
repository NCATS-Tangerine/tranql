from pyparsing import (
    Combine, Word, White, Literal, delimitedList, Optional, Empty, Suppress,
    Group, alphas, alphanums, printables, Forward, oneOf, quotedString,
    ZeroOrMore, restOfLine, CaselessKeyword, ParserElement, LineEnd,
    removeQuotes, Regex, nestedExpr, pyparsing_common as ppc)

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

concept_value = quotedString.setName('concept value')
concept_value_list = Group(LBRACK.suppress() + delimitedList(concept_value) + RBRACK.suppress())

arrow = \
        Group(Literal("-[") + concept_name + Literal("]->")) | \
        Group(Literal("<-[") + concept_name + Literal("]-")) | \
        Literal ("->") | \
        Literal ("<-")
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

function_body = Forward()
# Valid data types: TranQL variable, real, integer, string
arg = ident | realNum | intNum | quotedString
function_body <<= Word(alphanums+"_") + (
    Literal("(").suppress() + (delimitedList(function_body | arg) | Empty()) + Literal(")").suppress()
)
# Since asList is called in the TranQL ast, a function ends up being structured as ["my_function_name", ["my_arg1", "my_arg"] or ["add_int", [4, 7]]
# Accordingly, there is no way to distinguish a function from an actual list. Since asList is called, we cannot give function_body a name.
# Therefore, the most straightforward way is to set a parsing action which converts the function structure to an actual class.
# However, classes are not easily json serializable, so a dict struct will do
function_body.setParseAction(lambda toks: { "name" : toks[0], "args" : toks[1:] })

# need to add support for alg expressions
columnRval = function_body | realNum | intNum | quotedString.addParseAction(removeQuotes) | columnName | concept_value_list
whereCondition = Group(
    ( columnName + binop + (columnRval | Word(printables) ) ) |
    # ( columnName + in_ + concept_value_list) |
    # ( columnName + in_ + "(" + delimitedList( columnRval ) + ")" ) |
    # ( columnName + in_ + "(" + statement + ")" ) |
    # ( columnName + in_ + (columnRval | Word(printables))) |
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
                                   realNum |
                                   concept_value_list ))
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


""" Define the statement grammar. """
statement = Forward()

incomplete_arrow = \
        Group(Literal("-[") + (concept_name | Empty()) + Optional(Literal("]->"))) | \
        Group(Literal("<-[") + (concept_name | Empty()) + Optional(Literal("]-"))) | \
        Literal ("->") | \
        Literal ("<-") | \
        Literal ("-")


incomplete_question_graph_expression = ZeroOrMore(question_graph_element + incomplete_arrow) + Optional(question_graph_element)

# Match something like "from '/complete_this_" where there is a non completed string literal.
# In a group just so that it is consistent with an actual table which is stored in a list.
openTable = Group(delimitedList(tableNameList | Group((Literal('"') | Literal("'")) + Regex('.*'))))

statement <<= (
    Group(
        Group(SELECT + incomplete_question_graph_expression)("concepts") + Suppress(optWhite) +
        Optional(Group(FROM + (openTable | Empty()))) + Suppress(optWhite) +
        Optional(Group(WHERE + whereExpression("where"))) + Suppress(optWhite) +
        Optional(Group(SET + setExpression("set")))("select")
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
incomplete_program_grammar = statement + ZeroOrMore(statement)

incomplete_program_grammar.ignore (comment)
