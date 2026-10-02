import sys
import json
import ast
import operator

def eval_expr(expr):
    """
    Safely evaluate a mathematical string expression using AST.
    """
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
        ast.USub: operator.neg
    }

    def _eval(node):
        if isinstance(node, ast.Constant): # python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return ops[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
            return ops[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    return _eval(ast.parse(expr, mode='eval').body)


def run():
    if len(sys.argv) < 2:
        print("Error: Calculator tool requires an equation parameter.")
        return

    try:
        args = json.loads(sys.argv[1])
        equation = args.get("equation")

        if not equation:
            print("Error: Missing 'equation' in parameters.")
            return

        # Clean up the equation string a bit just in case
        equation = str(equation).replace('^', '**')

        result = eval_expr(equation)
        print(f"Calculator Result: {equation} = {result}")

    except SyntaxError:
        print(f"Calculator Error: Malformed math expression: {equation}")
    except ZeroDivisionError:
        print(f"Calculator Error: Division by zero is not allowed.")
    except Exception as e:
        print(f"Calculator Error: {str(e)}")

if __name__ == "__main__":
    run()