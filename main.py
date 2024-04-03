import ctypes
import sys

# High Level Code
hlc = """
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

# Define an array with unsigned elements
unsigned_array = {'a': ctypes.c_uint8(0), 'b': ctypes.c_uint8(0), 'c': ctypes.c_uint8(0)}
# Define an array with signed elements
signed_array = {'x': ctypes.c_int8(0), 'y': ctypes.c_int8(0), 'z': ctypes.c_int8(0)}
# Define an array with 8-bit wide registers
registers = {'eax': ctypes.c_int8(0), 'ebx': ctypes.c_int8(0), 'ecx': ctypes.c_int8(0), 'edx': ctypes.c_int8(0)}
if_count = 0
while_count = 0
relational_operators = {'<', '<=', '>', '>=', '==', '!='}
operators = ['+', '-', '*', '/']
variable = {}
memory = [0] * 1024  # 1kB byte-addressable memory
# Define mappings for variables, registers, and flags along with their corresponding addresses
mapping = {
    'a': '01',
    'b': '02',
    'c': '03',
    'x': '04',
    'y': '05',
    'z': '06',
    'eax': '07',
    'ebx': '08',
    'ecx': '09',
    'edx': '0A',
    'CF': '0B',
    'OF': '0C',
    'SF': '0D',
    'ZF': '0E',
    '__$EncStackInitStart': 'A0'
}
# Define the mapping between YMC instructions and machine code
ymc_to_machine_code = {
    'vrmov': '10',
    'vmmov': '11',
    'rmmov': '12',
    'mrmov': '13',
    'rrmov': '14',
    'mmmov': '15',
    'cmp': '20',
    'iaddmul': '42',
    'iadddiv': '43',
    'isubmul': '46',
    'isubdiv': '47',
    'imuladd': '48',
    'imulsub': '49',
    'imulmul': '4A',
    'imuldiv': '4B',
    'idivadd': '4C',
    'idivsub': '4D',
    'idivmul': '4E',
    'idivdiv': '4F',
    'addadd': '50',
    'addsub': '51',
    'addmul': '52',
    'adddiv': '53',
    'subadd': '54',
    'subsub': '55',
    'submul': '56',
    'subdiv': '57',
    'muladd': '58',
    'mulsub': '59',
    'mulmul': '5A',
    'muldiv': '5B',
    'divadd': '5C',
    'divsub': '5D',
    'divmul': '5E',
    'divdiv': '5F',
    'add': '60',
    'sub': '61',
    'mul': '62',
    'div': '63',
    'imul': '64',
    'idiv': '65',
    'jmp': '70',
    'jle': '71',
    'jl': '72',
    'je': '73',
    'jne': '74',
    'jge': '75',
    'jg': '76',
    'call': '90'
}


def check_variables(variable):
    # Look up the address for the variable
    address = mapping.get(variable, 'Unknown')  # Return 'Unknown' if the variable does not exist
    if address == 'Unknown':
        print("Error: " + variable + " is not defined!")


def check_ymc_code(ymc_code):
    # Look up the machine code
    machine_codes = ymc_to_machine_code.get(ymc_code, 'Unknown')  # Return 'Unknown' if machine code is not found
    if machine_codes == 'Unknown':
        print("Error: " + ymc_code + " is not defined!")


def parse_hlc_code(hlc):
    for line in hlc.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('unsigned'):
            _, var_list = line.split(' ', 1)
            var_list = var_list.split()
            if len(var_list) > 3:
                print("Error: unsigned variables more than 3, please leave 3 variables in this line!")
                sys.exit()
            for var_name in var_list:
                unsigned_array[var_name] = ctypes.c_uint8(0)
        elif line.startswith('signed'):
            _, var_list = line.split(' ', 1)
            var_list = var_list.split()
            if len(var_list) > 3:
                print("Error: signed variables more than 3, please leave 3 variables in this line!")
                sys.exit()
            for var_name in var_list:
                signed_array[var_name] = ctypes.c_int8(0)
        elif line.startswith('if'):
            line_if = line.split()
            if len(line_if) == 4 and line_if[3] in relational_operators:
                continue
            else:
                print("Error: Only one relational operator is allowed in if statements.")
                sys.exit()
        elif line.startswith('while'):
            line_while = line.split()
            if len(line_while) == 4 and line_while[3] in relational_operators:
                continue
            else:
                print("Error: Only one relational operator is allowed in if statements.")
                sys.exit()
        elif '=' in line:
            var, expr = line.split('=')
            var = var.strip()
            expr = expr.strip()
            check_formula(expr)
            left_type = variable.get(var)
            if left_type is not None:
                right_type = variable.get(expr)
                if right_type is None:
                    continue
                if left_type != right_type:
                    print(f"Error: Inconsistent variable types for '{var}' and '{expr}'")
                    sys.exit()
            else:
                variable[var] = expr
            instructions.append(('assign', var, expr))

        print("Instructions:", instructions)
    return variable, instructions


def check_formula(expr):
    operator_count = sum(expr.count(op) for op in operators)
    if operator_count > 2:
        print("Error: The formula has more than 2 operators.")
        sys.exit()


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


variables, instructions = parse_hlc_code(hlc_code)
machine_code = generate_assembly_code(variables, instructions)
print('Generated Assembly Code:', machine_code)
