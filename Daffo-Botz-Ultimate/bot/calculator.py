"""Bounded arithmetic interpreter. Never evaluates Python code."""
import ast
import math
import operator
import re

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
FUNCS = {'sqrt': math.sqrt, 'abs': abs, 'round': round, 'sin': math.sin,
         'cos': math.cos, 'tan': math.tan, 'log': math.log, 'log10': math.log10}

def calculate(expression):
    text = str(expression).strip().lower()
    if not text or len(text) > 240:
        raise ValueError('Rumus wajib diisi, maksimal 240 karakter.')
    for word, symbol in [('ditambah','+'),('tambah','+'),('plus','+'),('dikurangi','-'),('kurang','-'),('minus','-'),('dikali','*'),('kali','*'),('dibagi','/'),('bagi','/'),('pangkat','**')]:
        text = re.sub(r'\b'+word+r'\b', symbol, text)
    text = text.replace('×','*').replace('÷','/').replace('^','**').replace('−','-')
    text = re.sub(r'(?<=\d)\s*x\s*(?=[\d(])', '*', text)
    text = re.sub(r'(?<=\d),(?=\d)', '.', text)
    text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'(\1/100)', text)
    text = re.sub(r'\bakar\s*\(', 'sqrt(', text)
    try:
        tree = ast.parse(text.strip(), mode='eval')
        if len(list(ast.walk(tree))) > 90: raise ValueError('Rumus terlalu kompleks.')
        def visit(node, depth=0):
            if depth > 16: raise ValueError('Rumus terlalu bertingkat.')
            if isinstance(node, ast.Expression): return visit(node.body, depth+1)
            if isinstance(node, ast.Constant) and type(node.value) in (int,float): value=node.value
            elif isinstance(node, ast.Name) and node.id in ('pi','e'): value=getattr(math,node.id)
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                value=visit(node.operand,depth+1)*(1 if isinstance(node.op,ast.UAdd) else -1)
            elif isinstance(node, ast.BinOp):
                a,b=visit(node.left,depth+1),visit(node.right,depth+1)
                if isinstance(node.op,ast.Pow):
                    if abs(b)>100 or (a and abs(a)>1 and b*math.log10(abs(a))>100): raise ValueError('Pangkat terlalu besar.')
                    value=a**b
                elif type(node.op) in OPS: value=OPS[type(node.op)](a,b)
                else: raise ValueError('Operator tidak didukung.')
            elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in FUNCS and not node.keywords and 1<=len(node.args)<=2:
                value=FUNCS[node.func.id](*(visit(x,depth+1) for x in node.args))
            else: raise ValueError('Hanya angka, operasi matematika, dan fungsi yang didukung.')
            if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1e100: raise ValueError('Hasil di luar batas.')
            return value
        value=visit(tree)
        return str(value) if isinstance(value,int) else format(value,'.12g')
    except ZeroDivisionError: raise ValueError('Tidak bisa membagi dengan nol.') from None
    except (SyntaxError,TypeError,OverflowError): raise ValueError('Rumus tidak valid. Contoh: (12+8) × 3 / 2, 2^8, sqrt(81), 15% * 200000.') from None
