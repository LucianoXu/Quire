
from ...mTLC.env import Env
from ..prover.ast import RemAst


from .prover_parsing_build import parse_sentence, ParsingError, LexingError, ValueError

from ..language import AstPres

from ..prover.prover import Prover, Frame

import numpy as np

from ...qplcomp import prepare_env

class MLS:
    '''
    A micro language server for Rem langauge.

    it integrates the parser, pass input to prover and pass the output to TUI
    '''

    def __init__(self):
        self.prover = Prover(prepare_env())

        self.cmd_stack: list[RemAst] = []

        # the index of the last charactor of the command (typically, '.')
        self.code_stack: list[str] = []  

        self.selected_frame_id = -1

        self.error : str = ''

    @property
    def verified_code(self) -> str:
        return ''.join(self.code_stack)

    @property
    def prover_info(self) -> str:
        # note that the prover frame is always one frame longer because of the initial one
        return str(self.selected_frame)
    

    @property
    def selected_frame(self) -> Frame:
        return self.prover.frame_stack[self.selected_frame_id+1]
    
    @property
    def selected_goal(self) -> AstPres | None:
        return self.selected_frame.current_goals[0] if len(self.selected_frame.current_goals) > 0 else None
    
    @property
    def latest_selected(self) -> bool:
        '''
        Check whether the latest frame is selected.
        '''
        return self.selected_frame_id == len(self) - 1
    
    
    def __len__(self) -> int:
        return len(self.cmd_stack)
    
    def set_cursor(self, pos: int) -> None:
        '''
        set the cursor to the position and select the frame accordingly
        '''
        # calculate the current frame
        new_frame_id = -1
        total_len = 0
        for code in self.code_stack:
            new_frame_id += 1
            total_len += len(code)
            if total_len >= pos:
                break

        self.selected_frame_id = new_frame_id
            

    def step_forward(self, new_code: str) -> tuple[str, str|None] | None:
        '''
        step forward

        If succeeded, return the unparsed code and output. 
        Else return None.
        '''

        self.error = ''
        
        # STEP 1, parse the command
        res, remaining = parse_sentence(self.prover.current_frame.env, new_code)

        if isinstance(res, Exception):
            self.error = str(res)
            return None
        
        # res: tuple[RemAst, str]

        # STEP 2, execute the command
        try:
            output = self.prover.execute(res[0])

        except Exception as e:
            self.error = str(e)
            return None

        self.cmd_stack.append(res[0])
        self.code_stack.append(res[1])

        # focus on the latest frame
        self.selected_frame_id = len(self) - 1

        return remaining, output

    def step_backward(self) -> str|None:
        '''
        step backward

        if succeeded, return the code popped. Else return None.
        '''
        self.error = ''

        if len(self) == 0:
            self.error = "No more steps to go back."
            return None
        
        else:
            res = self.code_stack.pop()
            self.cmd_stack.pop()
            self.prover.pop_frame()

        # adjust selected_frame_id
        self.selected_frame_id = len(self) - 1

        return res
