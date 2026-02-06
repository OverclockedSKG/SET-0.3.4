import sys
import re

# =========================
# TOKEN
# =========================

class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"{self.type}:{self.value}"

# =========================
# LEXER
# =========================

class Lexer:
    token_spec = [
        ("NUMBER",   r"\d+(\.\d+)?"),
        ("STRING",   r'"[^"]*"'),
        ("EQ",       r"eq"),
        ("NEQ",      r"neq"),
        ("LT",       r"lt"),
        ("GT",       r"gt"),
        ("LE",       r"le"),
        ("GE",       r"ge"),
        ("AND",      r"and"),
        ("OR",       r"or"),
        ("PL",       r"pl"),
        ("MN",       r"mn"),
        ("DP",       r"dp"),
        ("NP",       r"np"),
        ("VAR",      r"var"),
        ("INT",      r"int"),
        ("FLT",      r"flt"),
        ("BOOL",     r"bool"),
        ("SET",      r"set"),
        ("IF",       r"if"),
        ("WSET",     r"wset"),
        ("FCE",      r"fce"),
        ("TRY",      r"try"),
        ("CATCH",    r"catch"),
        ("TRUE",     r"true"),
        ("FALSE",    r"false"),
        ("LEN",      r"len"),
        ("INP",      r"inp"),
        ("IDENT",    r"[a-zA-Z_]\w*"),
        ("ASSIGN",   r"="),
        ("LBRACE",   r"\{"),
        ("RBRACE",   r"\}"),
        ("COLON",    r":"),
        ("SKIP",     r"[ \t]+"),
        ("NEWLINE",  r"\n"),
    ]

    def __init__(self, code):
        self.code = code

    def tokenize(self):
        tokens=[]
        regex="|".join(f"(?P<{n}>{p})" for n,p in self.token_spec)
        for line in self.code.splitlines():
            line=line.split("#",1)[0]
            for m in re.finditer(regex,line):
                k=m.lastgroup
                v=m.group()
                if k=="NUMBER":
                    tokens.append(Token("NUMBER", float(v) if "." in v else int(v)))
                elif k=="STRING":
                    tokens.append(Token("STRING", v[1:-1]))
                elif k in ("SKIP","NEWLINE"):
                    continue
                else:
                    tokens.append(Token(k,v))
        return tokens

# =========================
# PARSER
# =========================

class Parser:
    def __init__(self,tokens):
        self.tokens=tokens
        self.pos=0

    def current(self):
        return self.tokens[self.pos] if self.pos<len(self.tokens) else None

    def eat(self,t):
        tok=self.current()
        if tok and tok.type==t:
            self.pos+=1
            return tok
        raise RuntimeError("parser desync")

    def parse(self):
        stmts=[]
        while self.current():
            stmt=self.statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts

    def statement(self):
        tok=self.current()
        if not tok:
            return None

        # IGNORE stray tokens completely
        if tok.type in ("STRING","NUMBER","TRUE","FALSE"):
            self.pos+=1
            return None

        if tok.type=="VAR": return self.var_decl()
        if tok.type=="SET": return self.set_stmt()
        if tok.type=="IF": return self.if_stmt()
        if tok.type=="WSET": return self.wset_stmt()
        if tok.type=="FCE": return self.fce_stmt()
        if tok.type=="TRY": return self.try_stmt()

        # Unknown tokens are skipped silently
        self.pos+=1
        return None

    def var_decl(self):
        self.eat("VAR")
        t=self.eat(self.current().type).type
        name=self.eat("IDENT").value
        self.eat("ASSIGN")
        val=self.expr()
        return ("VAR",t,name,val)

    def set_stmt(self):
        self.eat("SET")
        return ("SET",self.expr())

    def if_stmt(self):
        self.eat("IF")
        cond=self.expr()
        then=self.block_or_stmt()
        else_=None
        if self.current() and self.current().type=="COLON":
            self.eat("COLON")
            else_=self.block_or_stmt()
        return ("IF",cond,then,else_)

    def wset_stmt(self):
        self.eat("WSET")
        return ("WSET",self.expr(),self.block_or_stmt())

    def fce_stmt(self):
        self.eat("FCE")
        return ("FCE",self.eat("IDENT").value)

    def try_stmt(self):
        self.eat("TRY")
        t=self.block_or_stmt()
        self.eat("CATCH")
        c=self.block_or_stmt()
        return ("TRY",t,c)

    def block_or_stmt(self):
        if self.current() and self.current().type=="LBRACE":
            self.eat("LBRACE")
            s=[]
            while self.current() and self.current().type!="RBRACE":
                st=self.statement()
                if st: s.append(st)
            self.eat("RBRACE")
            return ("BLOCK",s)
        return self.statement()

    def expr(self):
        n=self.factor()
        while self.current() and self.current().type in (
            "PL","MN","DP","NP","EQ","NEQ","LT","GT","LE","GE","AND","OR"):
            op=self.current().type
            self.eat(op)
            n=(op,n,self.factor())
        return n

    def factor(self):
        tok=self.current()
        if tok.type=="NUMBER": self.eat("NUMBER"); return ("NUM",tok.value)
        if tok.type=="STRING": self.eat("STRING"); return ("STR",tok.value)
        if tok.type=="TRUE": self.eat("TRUE"); return ("BOOL",True)
        if tok.type=="FALSE": self.eat("FALSE"); return ("BOOL",False)
        if tok.type=="IDENT": self.eat("IDENT"); return ("VARREF",tok.value)
        if tok.type=="INP": self.eat("INP"); return ("INP",)
        if tok.type=="LEN": self.eat("LEN"); return ("LEN",self.factor())
        raise RuntimeError("bad expr")

# =========================
# INTERPRETER
# =========================

class Interpreter:
    def __init__(self):
        self.vars={}
        self.funcs={"hello":[("SET",("STR","hello function"))]}

    def eval(self,n):
        t=n[0]
        if t=="NUM": return n[1]
        if t=="STR": return n[1]
        if t=="BOOL": return n[1]
        if t=="VARREF": return self.vars.get(n[1],0)
        if t=="INP": return input()
        if t=="LEN": return len(self.eval(n[1]))
        if t=="PL": return self.eval(n[1])+self.eval(n[2])
        if t=="MN": return self.eval(n[1])-self.eval(n[2])
        if t=="DP": return self.eval(n[1])*self.eval(n[2])
        if t=="NP": return self.eval(n[1])/self.eval(n[2])
        if t=="EQ": return self.eval(n[1])==self.eval(n[2])
        if t=="NEQ": return self.eval(n[1])!=self.eval(n[2])
        if t=="LT": return self.eval(n[1])<self.eval(n[2])
        if t=="GT": return self.eval(n[1])>self.eval(n[2])
        if t=="LE": return self.eval(n[1])<=self.eval(n[2])
        if t=="GE": return self.eval(n[1])>=self.eval(n[2])
        if t=="AND": return self.eval(n[1]) and self.eval(n[2])
        if t=="OR": return self.eval(n[1]) or self.eval(n[2])

    def run(self,stmts):
        for s in stmts:
            t=s[0]
            if t=="VAR":
                _,tp,n,v=s
                val=self.eval(v)
                self.vars[n]=int(val) if tp=="INT" else float(val) if tp=="FLT" else val
            elif t=="SET":
                print(self.eval(s[1]))
            elif t=="IF":
                _,c,th,el=s
                self.run([th]) if self.eval(c) else el and self.run([el])
            elif t=="WSET":
                _,c,b=s
                while self.eval(c): self.run([b])
            elif t=="BLOCK":
                self.run(s[1])
            elif t=="FCE":
                if s[1] in self.funcs: self.run(self.funcs[s[1]])
            elif t=="TRY":
                try: self.run([s[1]])
                except: self.run([s[2]])

# =========================
# RUNNER
# =========================

def run_code(code):
    print("SET v0.3.4 – Syntax Easy To-use\n")
    tokens=Lexer(code).tokenize()
    tree=Parser(tokens).parse()
    Interpreter().run(tree)

if __name__=="__main__":
    with open(sys.argv[1]) as f:
        run_code(f.read())
