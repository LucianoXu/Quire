

#############################################################
# the lexer

import ply.lex as lex

from .lexer_def import *

# Build the lexer
import re
lexer = lex.lex(reflags = re.UNICODE)



#############################################################
# the parser

import ply.yacc as yacc

from .parser_def import *

# Build the parser
parser = yacc.yacc()





#############################################################
# the encapsulation 

from ..env import Env, TypedTerm

from ..qval import qvallib, QOpt, QSOpt

from .eqopt import EQOpt
from .eqso import EQSOpt 



def prepare_env() -> Env:
    '''
    Append the environment with predefined quantum values.
    '''
    env = Env()
    for key in qvallib:
        val = qvallib[key]
        if isinstance(val, QOpt):
            env[key] = EQOpt(val)
        elif isinstance(val, QSOpt):
            env[key] = EQSOpt(val)
        else:
            raise Exception("Unexpected Exception.")
    
    return env


class Parser:

    @staticmethod
    def parse(code : str) -> TypedTerm:
        res = parser.parse(code)
        if not isinstance(res, TypedTerm):
            raise Exception("Unexpected Exception.")
        
        return res


# assign the environment for parser
from . import parser_def