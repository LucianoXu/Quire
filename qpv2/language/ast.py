from __future__ import annotations

from qplcomp import IQOpt
from qplcomp import Expr, QVar, IQOpt, expr_type_check

INDENT = "  "

class Ast:

    def __init__(self):
        '''
        This `SRefined` attribute can refer to the subsequent refined programs for this program. If `None`, then the current program is used.
        '''
        self.SRefined : Ast | None = None

    def refine(self, SRefined : Ast) -> None:
        '''
        refine with `SRefined` and check the validity.
        '''
        raise NotImplementedError()

    @property
    def definite(self) -> bool:
        '''
        Whether this program is definite. In other words, whether there is no prescription statements in this program.
        '''
        raise NotImplementedError()
    
    def prefix_str_current_only(self, prefix = "") -> str:
        '''
        return the formatted program (without the `SRefined` part)
        '''
        raise NotImplementedError()

    
    def prefix_str(self, prefix = "") -> str:
        res = self.prefix_str_current_only(prefix)
        if self.SRefined is None:
            return res
        else:
            res += "\n" + prefix + INDENT + "==> {\n"
            res += self.SRefined.prefix_str(prefix) + " }"
            return res

    def __str__(self) -> str:
        return self.prefix_str()
    
    @property
    def extract(self) -> Ast:
        '''
        Extract the refinement result as a program syntax (without refinement proofs).
        '''
        if self.SRefined is not None:
            return self.SRefined.extract
        else:
            return self
    
    def wlp(self, post : IQOpt) -> IQOpt:
        '''
        Calculate the weakest liberal precondition.
        '''
        raise NotImplementedError()


class AstAbort(Ast):
    def __init__(self):
        super().__init__()

    @property
    def definite(self) -> bool:
        return True
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + "abort"
    
    def wlp(self, post: IQOpt) -> IQOpt:
        return IQOpt.identity(False)


class AstSkip(Ast):
    def __init__(self):
        super().__init__()

    @property
    def definite(self) -> bool:
        return True
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + "skip"
    
    def wlp(self, post: IQOpt) -> IQOpt:
        return post


class AstInit(Ast):
    def __init__(self, eqvar : Expr):
        super().__init__()
        expr_type_check(eqvar, QVar)
        self._eqvar = eqvar

    @property
    def qvar(self) -> QVar:
        return self._eqvar.eval()   # type: ignore

    @property
    def definite(self) -> bool:
        return True
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + str(self._eqvar) + ":=0"
    
    def wlp(self, post: IQOpt) -> IQOpt:
        return post.initwlp(self.qvar)

    
class AstUnitary(Ast):
    def __init__(self, eU : Expr):
        super().__init__()
        expr_type_check(eU, IQOpt)

        # check whether this is a unitary
        if not eU.eval().qval.is_unitary:   # type: ignore
            raise ValueError("The operator '" + str(eU) + "' for unitary statement is not unitary.")
        
        self._eU = eU

    @property
    def U(self) -> IQOpt:
        return self._eU.eval()  # type: ignore

    @property
    def definite(self) -> bool:
        return True
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + str(self._eU)

    def wlp(self, post: IQOpt) -> IQOpt:
        U = self.U
        return U.dagger() @ post @ U
    

class AstAssert(Ast):
    def __init__(self, eP : Expr):
        super().__init__()
        expr_type_check(eP, IQOpt)

        # check whether this is a projector
        if not eP.eval().qval.is_projector: # type: ignore
            raise ValueError("The operator '" + str(eP) + "' for assertion statement is not projective.")
        
        self._eP = eP

    @property
    def P(self) -> IQOpt:
        return self._eP.eval()  # type: ignore

    @property
    def definite(self) -> bool:
        return True
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + "assert " + str(self._eP)
    
    def wlp(self, post: IQOpt) -> IQOpt:
        return self.P.Sasaki_imply(post)

    

class AstPres(Ast):
    def __init__(self, eP : Expr, eQ : Expr):
        super().__init__()
        expr_type_check(eP, IQOpt)
        expr_type_check(eQ, IQOpt)

        # check whether P and Q are projectors
        if not eP.eval().qval.is_projector: # type: ignore
            raise ValueError("The operator '" + str(eP) + "' for assertion statement is not projective.")
        if not eQ.eval().qval.is_projector: # type: ignore
            raise ValueError("The operator '" + str(eQ) + "' for assertion statement is not projective.")
        
        self._eP = eP
        self._eQ = eQ

    @property
    def P(self) -> IQOpt:
        return self._eP.eval()  # type: ignore

    @property
    def Q(self) -> IQOpt:
        return self._eQ.eval()  # type: ignore


    def refine(self, SRefined: Ast) -> None:
        '''
        For prescriptions, it checks the weakest precondition.
        '''
        if not self.P <= SRefined.wlp(self.Q):
            raise ValueError("The relation P <= wlp.S.Q is not satisfied.")
        
        self.SRefined = SRefined

    @property
    def definite(self) -> bool:
        return False
    
    def prefix_str_current_only(self, prefix="") -> str:
        return prefix + "[ pre: " + str(self._eP) + ", post: " + str(self._eQ) + " ]"


    def wlp(self, post: IQOpt) -> IQOpt:
        if post == IQOpt.identity(False):
            return IQOpt.identity(False)
        elif self.Q <= post:
            return self.P
        else:
            return IQOpt.zero(False)


class AstSeq(Ast):
    def __init__(self, S0 : Ast, S1 : Ast):
        super().__init__()
        self._S0 = S0
        self._S1 = S1

    @property
    def S0(self) -> Ast:
        return self._S0

    @property
    def S1(self) -> Ast:
        return self._S1
    
    @property
    def definite(self) -> bool:
        return self._S0.definite and self._S1.definite
    
    def prefix_str_current_only(self, prefix="") -> str:
        return self._S0.prefix_str(prefix) + ";\n" + self._S1.prefix_str(prefix)
    
    @property
    def extract(self) -> Ast:
        if self.SRefined is not None:
            return self.SRefined.extract
        else:
            return AstSeq(self.S0.extract, self.S1.extract)
    
    def wlp(self, post: IQOpt) -> IQOpt:
        return self.S0.wlp(self.S1.wlp(post))

class AstProb(Ast):
    def __init__(self, S0 : Ast, S1 : Ast, p : float):
        super().__init__()
        self._S0 = S0
        self._S1 = S1
        
        if p < 0 or p > 1:
            raise ValueError("Invalid probability: '" + str(p) + "'.")
        
        self._p = p

    @property
    def S0(self) -> Ast:
        return self._S0

    @property
    def S1(self) -> Ast:
        return self._S1
    
    @property
    def p(self) -> float:
        return self._p


    @property
    def definite(self) -> bool:
        return self._S0.definite and self._S1.definite
    
    def prefix_str_current_only(self, prefix="") -> str:
        res = prefix + "(\n" + self._S0.prefix_str(prefix + INDENT) + "\n"
        res += prefix + "_" + str(self._p) + "⊗\n"
        res += self._S1.prefix_str(prefix + INDENT) + "\n"
        res += prefix + ")"
        return res
    
    @property
    def extract(self) -> Ast:
        if self.SRefined is not None:
            return self.SRefined.extract
        else:
            return AstProb(self.S0.extract, self.S1.extract, self.p)
        
    def wlp(self, post: IQOpt) -> IQOpt:
        return self.S0.wlp(post) & self.S1.wlp(post)
    

class AstIf(Ast):
    def __init__(self, eP : Expr, S1 : Ast, S0 : Ast):
        super().__init__()
        expr_type_check(eP, IQOpt)

        # check whether P is a projector
        if not eP.eval().qval.is_projector: # type: ignore
            raise ValueError("The operator '" + str(eP) + "' for assertion statement is not projective.")
        
        self._eP = eP
        self._S1 = S1
        self._S0 = S0
    
    @property
    def P(self) -> IQOpt:
        return self._eP.eval()  # type: ignore
    
    @property
    def S1(self) -> Ast:
        return self._S1

    @property
    def S0(self) -> Ast:
        return self._S0



    @property
    def definite(self) -> bool:
        return self._S1.definite and self._S0.definite
    
    def prefix_str_current_only(self, prefix="") -> str:
        res = prefix + "if " + str(self._eP) + " then\n"
        res += self._S1.prefix_str(prefix + INDENT) + "\n"
        res += prefix + "else\n"
        res += self._S0.prefix_str(prefix + INDENT) + "\n"
        res += prefix + "end"
        return res

    @property
    def extract(self) -> Ast:
        if self.SRefined is not None:
            return self.SRefined.extract
        else:
            return AstIf(self._eP, self.S1.extract, self.S0.extract)

    def wlp(self, post: IQOpt) -> IQOpt:
        return self.P.Sasaki_imply(self.S1.wlp(post)) &\
              (~ self.P).Sasaki_imply(self.S0.wlp(post))


class AstWhile(Ast):
    def __init__(self, eP : Expr, S : Ast):
        super().__init__()
        expr_type_check(eP, IQOpt)

        # check whether P is a projector
        if not eP.eval().qval.is_projector: # type: ignore
            raise ValueError("The operator '" + str(eP) + "' for assertion statement is not projective.")
        
        self._eP = eP
        self._S = S

    @property
    def P(self) -> IQOpt:
        return self._eP.eval()  # type: ignore

    @property
    def S(self) -> Ast:
        return self._S
    
    @property
    def definite(self) -> bool:
        return self._S.definite
    
    def prefix_str_current_only(self, prefix="") -> str:
        res = prefix + "while " + str(self._eP) + " do\n"
        res += self._S.prefix_str(prefix + INDENT) + "\n"
        res += prefix + "end"
        return res

    @property
    def extract(self) -> Ast:
        if self.SRefined is not None:
            return self.SRefined.extract
        else:
            return AstWhile(self._eP, self.S.extract)

    def wlp(self, post: IQOpt) -> IQOpt:
        flag = True
        Rn = IQOpt.identity(False)
        Rn_1 = IQOpt.identity(False)

        # this is guaranteed to terminate
        while flag:
            Rn = Rn_1
            Rn_1 = self.P.Sasaki_imply(self.S.wlp(Rn)) & (~ self.P).Sasaki_imply(post)

            flag = not Rn == Rn_1

        return Rn

