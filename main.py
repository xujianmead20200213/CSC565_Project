from pyasmjit import Assembler

def parse_hlc_code(hlc_code):
    variables = {}
    instructions = []
    for line in hlc_code.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('unsigned') or line.startswith('signed'):
            # 解析变量声明语句
            _, var_list = line.split(' ', 1)
            for var_name in var_list.split():
                variables[var_name] = 0  # 初始化变量为0
        elif line.startswith('if') or line.startswith('else') or line.startswith('while'):
            # 解析控制流语句
            instructions.append(('control', line))
        elif '=' in line:
            # 解析赋值语句
            var, expr = line.split('=')
            variables[var.strip()] = expr.strip()
            instructions.append(('assign', var.strip(), expr.strip()))
    return variables, instructions

def generate_assembly_code(variables, instructions):
    asm = Assembler()
    for instr_type, instr in instructions:
        if instr_type == 'assign':
            var, expr = instr
            if '+' in expr:
                operand1, operand2 = expr.split('+')
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.add('eax', variables.get(operand2.strip(), operand2.strip()))
                asm.mov(variables[var], 'eax')
            elif '-' in expr:
                operand1, operand2 = expr.split('-')
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.sub('eax', variables.get(operand2.strip(), operand2.strip()))
                asm.mov(variables[var], 'eax')
            elif '*' in expr:
                operand1, operand2 = expr.split('*')
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.imul('eax', variables.get(operand2.strip(), operand2.strip()))
                asm.mov(variables[var], 'eax')
            elif '/' in expr:
                operand1, operand2 = expr.split('/')
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.cdq()
                asm.idiv(variables.get(operand2.strip(), operand2.strip()))
                asm.mov(variables[var], 'eax')
        elif instr_type == 'control':
            asm_label = asm.new_label()
            if instr.startswith('if'):
                _, condition = instr.split('if')
                condition = condition.strip()
                operand1, operator, operand2 = condition.split()
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.cmp('eax', variables.get(operand2.strip(), operand2.strip()))
                if operator == '<=':
                    asm.jle(asm_label)
            elif instr.startswith('else'):
                asm.jmp(asm_label)
            elif instr.startswith('while'):
                _, condition = instr.split('while')
                condition = condition.strip()
                operand1, operator, operand2 = condition.split()
                asm_label_start = asm.new_label()
                asm_label_end = asm.new_label()
                asm.bind_label(asm_label_start)
                asm.mov('eax', variables.get(operand1.strip(), operand1.strip()))
                asm.cmp('eax', variables.get(operand2.strip(), operand2.strip()))
                if operator == '>':
                    asm.jle(asm_label_end)
                elif operator == '>=':
                    asm.jl(asm_label_end)
                elif operator == '<':
                    asm.jge(asm_label_end)
                elif operator == '<=':
                    asm.jg(asm_label_end)
                asm.jmp(asm_label_start)
                asm.bind_label(asm_label_end)
            asm.bind_label(asm_label)
    return asm.get_machine_code()

# 给定的高级语言代码
hlc_code = """
unsigned a b c
signed x y z
a = 3
b = 15 + a
c = b * a / 10
x = -5
y = 13
if c <= 10
    x = y + 10
    print x
    print y
else
    x = y - 20
    print x
    print y

while y > 0
    print y
    print \n
    print x
    print \n
    y = y - 1 
"""

variables, instructions = parse_hlc_code(hlc_code)
machine_code = generate_assembly_code(variables, instructions)
print('Generated Assembly Code:', machine_code)
