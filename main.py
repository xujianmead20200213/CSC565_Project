import ctypes
import sys
import csv
from ctypes import c_int8
from typing import Dict

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
# unsigned_array = {'a': ctypes.c_uint8(0), 'b': ctypes.c_uint8(0), 'c': ctypes.c_uint8(0)}
unsigned_array = {}
# Define an array with signed elements
# signed_array = {'x': ctypes.c_int8(0), 'y': ctypes.c_int8(0), 'z': ctypes.c_int8(0)}
signed_array = {}
# Define an array with 8-bit wide registers
registers = {'eax': ctypes.c_int8(0), 'ebx': ctypes.c_int8(0), 'ecx': ctypes.c_int8(0), 'edx': ctypes.c_int8(0)}
flags = {'SF': ctypes.c_int8(0), 'OF': ctypes.c_int8(0), 'ZF': ctypes.c_int8(0), 'CF': ctypes.c_int8(0)}
if_count = 0
while_count = 0
relational_operators = ['<', '<=', '>', '>=', '==', '!=']
operators = ['+', '-', '*', '/']
variable = {}
memory = [format(0, '02x') for _ in range(1024)]  # 1kB byte-addressable memory
# Define mappings for variables, registers, and flags along with their corresponding addresses
mapping = {
    # 'a': '01',
    # 'b': '02',
    # 'c': '03',
    # 'x': '04',
    # 'y': '05',
    # 'z': '06',
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
action_spaces = {
    'vrmov': '3',
    'vmmov': '3',
    'rmmov': '3',
    'mrmov': '3',
    'rrmov': '3',
    'mmmov': '3',
    'cmp': '3',
    'iaddmul': '3',
    'iadddiv': '3',
    'isubmul': '3',
    'isubdiv': '3',
    'imuladd': '3',
    'imulsub': '3',
    'imulmul': '3',
    'imuldiv': '3',
    'idivadd': '3',
    'idivsub': '3',
    'idivmul': '3',
    'idivdiv': '3',
    'addadd': '3',
    'addsub': '3',
    'addmul': '3',
    'adddiv': '3',
    'subadd': '3',
    'subsub': '3',
    'submul': '3',
    'subdiv': '3',
    'muladd': '3',
    'mulsub': '3',
    'mulmul': '3',
    'muldiv': '3',
    'divadd': '3',
    'divsub': '3',
    'divmul': '3',
    'divdiv': '3',
    'add': '2',
    'sub': '2',
    'mul': '2',
    'div': '2',
    'imul': '2',
    'idiv': '2',
    'jmp': '2',
    'jle': '2',
    'jl': '2',
    'je': '2',
    'jne': '2',
    'jge': '2',
    'jg': '2',
    'call': '2'
}
convert_hlc_ymc = []
hlc_mapping_ymc = []
HLC_program = []
csv_title = ["HLC instruction", "YMC Address", "YMC assembly", "YMC encoding",
             "Modified registers (if any, after execution)", "Modified flags (if any, after execution)"]
HLC_program.append(csv_title)


def check_variables(variable_code):
    # Look up the address for the variable
    address = mapping.get(variable_code, 'Unknown')  # Return 'Unknown' if the variable does not exist
    if address == 'Unknown':
        print("Error: " + variable_code + " is not defined!")
    else:
        return address


def check_ymc_code(ymc_code):
    # Look up the machine code
    machine_codes = ymc_to_machine_code.get(ymc_code, 'Unknown')  # Return 'Unknown' if machine code is not found
    if machine_codes == 'Unknown':
        print("Error: " + ymc_code + " is not defined!")
    else:
        return machine_codes


def parse_hlc_code(hlc_code):
    # # Start with 0. Mark it as 1 if found while. Until finished mark it as 0
    # loop_flag = 0
    # Start with 0. Mark it as 1 if found while. Until finished mark it as 0
    jmp_address = 0
    if_else_flag = 0
    counter = 0
    counter_variable = 1
    for line in hlc_code.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('unsigned'):
            _, var_list = line.split(' ', 1)
            var_list = var_list.split()
            if len(var_list) > 3:
                print("Error: Unsigned variables more than 3, please leave 3 variables in this line!")
                sys.exit()
            for var_name in var_list:
                unsigned_array[var_name] = ctypes.c_uint8(0)
                variable[var_name] = ctypes.c_uint8(0)
                mapping[var_name] = "0" + str(counter_variable)
                counter_variable += 1
        elif line.startswith('signed'):
            _, var_list = line.split(' ', 1)
            var_list = var_list.split()
            if len(var_list) > 3:
                print("Error: Signed variables more than 3, please leave 3 variables in this line!")
                sys.exit()
            for var_name in var_list:
                signed_array[var_name] = ctypes.c_int8(0)
                variable[var_name] = ctypes.c_int8(0)
                mapping[var_name] = "0" + str(counter_variable)
                counter_variable += 1
        elif line.startswith('if'):
            if if_else_flag == 1:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if_else_flag = 1
            line_if = line.split()
            if len(line_if) == 4 and line_if[2] in relational_operators:
                # Todo Add here Convert HLC to YMC
                convert_hlc_ymc.append("add machine code here mark jump address here && change counter")
            else:
                print("Error: Only one relational operator is allowed in if statements.")
                sys.exit()
        elif line.startswith('else'):
            if if_else_flag == 0:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if_else_flag = 0
            line_else = line.split()
            if len(line_else) == 1:
                # Todo Add here Convert HLC to YMC
                convert_hlc_ymc.append("add machine code here fill the jump address here"
                                       " with the location + 1 && change counter")
            else:
                print("Error: Else statement is incorrect!")
                sys.exit()
        elif line.startswith('while'):
            line_while = line.split()
            if len(line_while) == 4 and line_while[2] in relational_operators:
                # Todo Add here Convert HLC to YMC
                convert_hlc_ymc.append("add machine code here fill the jump address here && change counter")
            else:
                print("Error: Only one relational operator is allowed in if statements.")
                sys.exit()
        elif '=' in line:
            var, expr = line.split('=')
            var = var.strip()
            expr = expr.strip()
            right_side = check_formula(expr)
            left_type = variable.get(var)
            if left_type is not None:
                if len(right_side) > 0:
                    if len(right_side) == 1:
                        right_type = variable.get(right_side[0])
                        if right_type is not None and type(left_type) != type(right_type):
                            print(f"Error: Inconsistent variable types for '{var}' and '{right_side[0]}'")
                            sys.exit()
                        else:
                            if right_type is not None:
                                instruction = "mrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            instruction = "rmmov eax " + var
                            counter = generate_assembly_code("rmmov", instruction, counter, line)
                    elif len(right_side) == 2 or len(right_side) == 4 or len(right_side) > 5:
                        print(f"Error: The formular is incorrect!")
                        sys.exit()
                    elif len(right_side) == 3:
                        right_type_1 = variable.get(right_side[0])
                        right_type_2 = variable.get(right_side[2])
                        if not (right_side[0].isnumeric() or right_type_1 is not None):
                            print("Error: The formula is incorrect!")
                            sys.exit()
                        if not (right_side[2].isnumeric() or right_type_2 is not None):
                            print("Error: The formula is incorrect!")
                            sys.exit()
                        if right_side[1] not in operators:
                            print(f"Error: The formular is incorrect!")
                            sys.exit()
                        elif ((right_type_1 is not None and type(left_type) != type(right_type_1))
                              or (right_type_2 is not None and type(left_type) != type(right_type_2))):
                            print(f"Error: Inconsistent variable types for"
                                  f" '{var}' and '{right_side[0]}' or '{right_side[2]}'")
                            sys.exit()
                        else:
                            if right_type_1 is not None:
                                instruction = "mrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if right_type_2 is not None:
                                instruction = "mrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if var in unsigned_array:
                                if right_side[1] == operators[0]:
                                    instruction = "add ebx"
                                    counter = generate_assembly_code("add", instruction, counter, line)
                                elif right_side[1] == operators[1]:
                                    instruction = "sub ebx"
                                    counter = generate_assembly_code("sub", instruction, counter, line)
                                elif right_side[1] == operators[2]:
                                    instruction = "mul ebx"
                                    counter = generate_assembly_code("mul", instruction, counter, line)
                                elif right_side[1] == operators[3]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "div ebx"
                                    counter = generate_assembly_code("div", instruction, counter, line)
                            if right_type_1 is not None:
                                instruction = "mrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if right_type_2 is not None:
                                instruction = "mrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if var in unsigned_array:
                                if right_side[1] == operators[0]:
                                    instruction = "add ebx"
                                    counter = generate_assembly_code("add", instruction, counter, line)
                                elif right_side[1] == operators[1]:
                                    instruction = "sub ebx"
                                    counter = generate_assembly_code("sub", instruction, counter, line)
                                elif right_side[1] == operators[2]:
                                    instruction = "mul ebx"
                                    counter = generate_assembly_code("mul", instruction, counter, line)
                                elif right_side[1] == operators[3]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "div ebx"
                                    counter = generate_assembly_code("div", instruction, counter, line)
                            else:
                                if right_side[1] == operators[0]:
                                    instruction = "add ebx"
                                    counter = generate_assembly_code("add", instruction, counter, line)
                                elif right_side[1] == operators[1]:
                                    instruction = "sub ebx"
                                    counter = generate_assembly_code("sub", instruction, counter, line)
                                elif right_side[1] == operators[2]:
                                    instruction = "imul ebx"
                                    counter = generate_assembly_code("imul", instruction, counter, line)
                                elif right_side[1] == operators[3]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "idiv ebx"
                                    counter = generate_assembly_code("idiv", instruction, counter, line)
                            instruction = "rmmov eax " + var
                            counter = generate_assembly_code("rmmov", instruction, counter, line)
                    elif len(right_side) == 5:
                        right_type_1 = variable.get(right_side[0])
                        right_type_2 = variable.get(right_side[2])
                        right_type_3 = variable.get(right_side[4])
                        if not (right_side[0].isnumeric() or right_type_1 is not None):
                            print("Error: The formula is incorrect!")
                            sys.exit()
                        if not (right_side[2].isnumeric() or right_type_2 is not None):
                            print("Error: The formula is incorrect!")
                            sys.exit()
                        if not (right_side[4].isnumeric() or right_type_3 is not None):
                            print("Error: The formula is incorrect!")
                            sys.exit()
                        if right_side[1] not in operators or right_side[3] not in operators:
                            print(f"Error: The formular is incorrect!")
                            sys.exit()
                        elif ((right_type_1 is not None and type(left_type) != type(right_type_1))
                              or (right_type_2 is not None and type(left_type) != type(right_type_2))
                              or (right_type_3 is not None and type(left_type) != type(right_type_3))):
                            print(f"Error: Inconsistent variable types for"
                                  f" '{var}' and '{right_side[0]}' or '{right_side[2]}' or '{right_side[4]}'")
                            sys.exit()
                        else:
                            if right_type_1 is not None:
                                instruction = "mrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[0] + " eax"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if right_type_2 is not None:
                                instruction = "mrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[2] + " ebx"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if right_type_3 is not None:
                                instruction = "mrmov " + right_side[4] + " ecx"
                                counter = generate_assembly_code("mrmov", instruction, counter, line)
                            else:
                                instruction = "vrmov " + right_side[4] + " ecx"
                                counter = generate_assembly_code("vrmov", instruction, counter, line)
                            if var in unsigned_array:
                                if right_side[1] == operators[0] and right_side[3] == operators[0]:
                                    instruction = "addadd ebx ecx"
                                    counter = generate_assembly_code("addadd", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[1]:
                                    instruction = "addsub ebx ecx"
                                    counter = generate_assembly_code("addsub", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[2]:
                                    instruction = "addmul ebx ecx"
                                    counter = generate_assembly_code("addmul", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "adddiv ebx ecx"
                                    counter = generate_assembly_code("adddiv", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[0]:
                                    instruction = "subadd ebx ecx"
                                    counter = generate_assembly_code("subadd", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[1]:
                                    instruction = "subsub ebx ecx"
                                    counter = generate_assembly_code("subsub", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[2]:
                                    instruction = "submul ebx ecx"
                                    counter = generate_assembly_code("submul", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "subdiv ebx ecx"
                                    counter = generate_assembly_code("subdiv", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[0]:
                                    instruction = "muladd ebx ecx"
                                    counter = generate_assembly_code("muladd", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[1]:
                                    instruction = "mulsub ebx ecx"
                                    counter = generate_assembly_code("mulsub", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[2]:
                                    instruction = "mulmul ebx ecx"
                                    counter = generate_assembly_code("mulmul", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "muldiv ebx ecx"
                                    counter = generate_assembly_code("muldiv", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[0]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "divadd ebx ecx"
                                    counter = generate_assembly_code("divadd", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[1]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "divsub ebx ecx"
                                    counter = generate_assembly_code("divsub", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[2]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "divmul ebx ecx"
                                    counter = generate_assembly_code("divmul", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[3]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "divdiv ebx ecx"
                                    counter = generate_assembly_code("divdiv", instruction, counter, line)
                            else:
                                if right_side[1] == operators[0] and right_side[3] == operators[0]:
                                    instruction = "addadd ebx ecx"
                                    counter = generate_assembly_code("addadd", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[1]:
                                    instruction = "addsub ebx ecx"
                                    counter = generate_assembly_code("addsub", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[2]:
                                    instruction = "iaddmul ebx ecx"
                                    counter = generate_assembly_code("iaddmul", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "iadddiv ebx ecx"
                                    counter = generate_assembly_code("iadddiv", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[0]:
                                    instruction = "subadd ebx ecx"
                                    counter = generate_assembly_code("subadd", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[1]:
                                    instruction = "subsub ebx ecx"
                                    counter = generate_assembly_code("subsub", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[2]:
                                    instruction = "isubmul ebx ecx"
                                    counter = generate_assembly_code("isubmul", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "isubdiv ebx ecx"
                                    counter = generate_assembly_code("isubdiv", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[0]:
                                    instruction = "imuladd ebx ecx"
                                    counter = generate_assembly_code("imuladd", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[1]:
                                    instruction = "imulsub ebx ecx"
                                    counter = generate_assembly_code("imulsub", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[2]:
                                    instruction = "imulmul ebx ecx"
                                    counter = generate_assembly_code("imulmul", instruction, counter, line)
                                elif right_side[1] == operators[2] and right_side[3] == operators[3]:
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "imuldiv ebx ecx"
                                    counter = generate_assembly_code("imuldiv", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[0]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "idivadd ebx ecx"
                                    counter = generate_assembly_code("idivadd", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[1]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "idivsub ebx ecx"
                                    counter = generate_assembly_code("idivsub", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[2]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "idivmul ebx ecx"
                                    counter = generate_assembly_code("idivmul", instruction, counter, line)
                                elif right_side[1] == operators[3] and right_side[3] == operators[3]:
                                    if right_side[2] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    if right_side[4] == 0:
                                        print(f"Error: The formular can divided by Zero!")
                                        sys.exit()
                                    instruction = "idivdiv ebx ecx"
                                    counter = generate_assembly_code("idivdiv", instruction, counter, line)
                            instruction = "rmmov eax " + var
                            counter = generate_assembly_code("rmmov", instruction, counter, line)
                else:
                    print(f"Error: Nothing on the right side!")
                    sys.exit()
            else:
                print(f"Error: The left side of this formular is incorrect!")
                sys.exit()


def check_formula(expr):
    operator_count = sum(expr.count(op) for op in operators)
    if operator_count > 2:
        print("Error: The formula has more than 2 operators.")
        sys.exit()
    else:
        return expr.split()


def value_get_key(value_find,mapper_find):
    key_find = [key for key, value in mapper_find.items() if value == value_find]
    return key_find


def save_csv_file(register_v, flag_v, hlc_code, memory_address, ymc_code, ymc_encoding):
    new_csv_line = [hlc_code, memory_address, ymc_code, ymc_encoding, register_v, flag_v]
    HLC_program.append(new_csv_line)


def generate_assembly_code(action, instruction, counter_c, hlc_code_line):
    if action == 'vrmov':
        # split the instruction
        var_list = instruction.split()
        # put the first instruction into memory according to table is the action like vrmov
        memory[counter_c] = ymc_to_machine_code.get(var_list[0])
        counter_c += 1
        convert_hlc_ymc.append(instruction)
        hlc_mapping_ymc.append(hlc_code_line)
        # put the second instruction into memory like value
        if variable.get(var_list[1]) is None:
            num = int(var_list[1])
            if num < 0:
                num = (1 << 8) + num
            hex_str = format(num, '02x')
            memory[counter_c] = hex_str
        else:
            memory[counter_c] = mapping.get(var_list[1])
        counter_c += 1
        convert_hlc_ymc.append(instruction)
        hlc_mapping_ymc.append(hlc_code_line)
        # put the third instruction into memory like register
        memory[counter_c] = mapping.get(var_list[2])
        counter_c += 1
        convert_hlc_ymc.append(instruction)
        hlc_mapping_ymc.append(hlc_code_line)
    elif action == 'vmmov':
        return '11'
    elif action == 'rmmov':
        return '12'
    elif action == 'mrmov':
        return '13'
    elif action == 'rrmov':
        return '14'
    elif action == 'mmmov':
        return '15'
    elif action == 'cmp':
        return '20'
    elif action == 'iaddmul':
        return '42'
    elif action == 'iadddiv':
        return '43'
    # Add more cases as needed
    # 'isubmul': '46',
    # 'isubdiv': '47',
    # 'imuladd': '48',
    # 'imulsub': '49',
    # 'imulmul': '4A',
    # 'imuldiv': '4B',
    # 'idivadd': '4C',
    # 'idivsub': '4D',
    # 'idivmul': '4E',
    # 'idivdiv': '4F',
    # 'addadd': '50',
    # 'addsub': '51',
    # 'addmul': '52',
    # 'adddiv': '53',
    # 'subadd': '54',
    # 'subsub': '55',
    # 'submul': '56',
    # 'subdiv': '57',
    # 'muladd': '58',
    # 'mulsub': '59',
    # 'mulmul': '5A',
    # 'muldiv': '5B',
    # 'divadd': '5C',
    # 'divsub': '5D',
    # 'divmul': '5E',
    # 'divdiv': '5F',
    # 'add': '60',
    # 'sub': '61',
    # 'mul': '62',
    # 'div': '63',
    # 'imul': '64',
    # 'idiv': '65',
    # 'jmp': '70',
    # 'jle': '71',
    # 'jl': '72',
    # 'je': '73',
    # 'jne': '74',
    # 'jge': '75',
    # 'jg': '76',
    # 'call': '90'

    else:
        print("Error: Unknown action.")
        sys.exit()
    return counter_c


def process_memory_instruction(memory_instruction):
    pointer = 0
    while len(memory_instruction) < pointer:
        machine_code = memory_instruction[pointer]
        action = value_get_key(machine_code, ymc_to_machine_code)
        action_space = action_spaces.get(action)
        action_start = pointer
        machine_code = str(machine_code)
        instruction = []
        while action_space > 1:
            pointer += 1
            action_space -= 1
            new_machine_code = memory_instruction[pointer]
            machine_code = machine_code + " " + str(new_machine_code)
            instruction.append(new_machine_code)
        process_function(action, instruction)
        save_csv_file(hlc_mapping_ymc[action_start], action_start,
                      convert_hlc_ymc[action_start], machine_code, registers, flags)


def process_function(action, instruction):
    if action == 'vrmov':
        value = instruction[0]
        register = value_get_key(instruction[1], mapping)
        registers[register] = value
        # flag changes like ZF,OF,CF,SF
        # All register changes
    elif action == 'vmmov':
        return '11'
    elif action == 'rmmov':
        return '12'
    elif action == 'mrmov':
        return '13'
    elif action == 'rrmov':
        return '14'
    elif action == 'mmmov':
        return '15'
    elif action == 'cmp':
        return '20'
    elif action == 'iaddmul':
        return '42'
    elif action == 'iadddiv':
        return '43'
    # Add more cases as needed
    # 'isubmul': '46',
    # 'isubdiv': '47',
    # 'imuladd': '48',
    # 'imulsub': '49',
    # 'imulmul': '4A',
    # 'imuldiv': '4B',
    # 'idivadd': '4C',
    # 'idivsub': '4D',
    # 'idivmul': '4E',
    # 'idivdiv': '4F',
    # 'addadd': '50',
    # 'addsub': '51',
    # 'addmul': '52',
    # 'adddiv': '53',
    # 'subadd': '54',
    # 'subsub': '55',
    # 'submul': '56',
    # 'subdiv': '57',
    # 'muladd': '58',
    # 'mulsub': '59',
    # 'mulmul': '5A',
    # 'muldiv': '5B',
    # 'divadd': '5C',
    # 'divsub': '5D',
    # 'divmul': '5E',
    # 'divdiv': '5F',
    # 'add': '60',
    # 'sub': '61',
    # 'mul': '62',
    # 'div': '63',
    # 'imul': '64',
    # 'idiv': '65',
    # 'jmp': '70',
    # 'jle': '71',
    # 'jl': '72',
    # 'je': '73',
    # 'jne': '74',
    # 'jge': '75',
    # 'jg': '76',
    # 'call': '90'
    else:
        print("Error: Unknown action.")
        sys.exit()


parse_hlc_code(hlc)
process_memory_instruction(memory)
# Write into CSV path
csv_file_path = 'C:/Users/DELL/Desktop/CSC565/Project/HLC-program.csv'
with open(csv_file_path, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    for row in HLC_program:
        csv_writer.writerow(row)
print("HLC CSV file have been created")

# Write into CSV path
memory_csv_file_path = 'C:/Users/DELL/Desktop/CSC565/Project/memory.csv'
with open(memory_csv_file_path, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(memory)
print("Memory CSV file have been created")
