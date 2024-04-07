import ctypes
import sys
import csv
import re
import pandas as pd


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
    print a
    print b
    print c
    x = y + 10
    print x
    print y
else
    x = y - 20
    print x
    print y

while y > 0
    print y
    print \\n
    print x
    print \\n
    y = y - 1 
"""

# Define an array with unsigned elements
# unsigned_array = {'a': ctypes.c_uint8(0), 'b': ctypes.c_uint8(0), 'c': ctypes.c_uint8(0)}
unsigned_array = {}
# Define an array with signed elements
# signed_array = {'x': ctypes.c_int8(0), 'y': ctypes.c_int8(0), 'z': ctypes.c_int8(0)}
signed_array = {}
# Define an array with 8-bit wide registers
registers = {'eax': format(0, '02x'), 'ebx': format(0, '02x'), 'ecx': format(0, '02x'), 'edx': format(0, '02x')}
flags = {'SF': 0, 'OF': 0, 'ZF': 0, 'CF': 0}
if_count = 0
while_count = 0
relational_operators = ['<', '<=', '>', '>=', '==', '!=']
operators = ['+', '-', '*', '/']
variable = {}
memory = [format(0, '02x') for _ in range(1024)]  # 1kB byte-addressable memory
# Define mappings for variables, registers, and flags along with their corresponding addresses
mapping = {
    'eax': '07',
    'ebx': '08',
    'ecx': '09',
    'edx': '0A',
    'CF': '0B',
    'OF': '0C',
    'SF': '0D',
    'ZF': '0E',
    '__$EncStackInitStart': 'A0',
    '\\n': '0F'
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
    'iaddadd': '40',
    'iaddsub': '41',
    'iaddmul': '42',
    'iadddiv': '43',
    'isubadd': '44',
    'isubsub': '45',
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
    'iadd': '64',
    'isub': '65',
    'imul': '66',
    'idiv': '67',
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
    'iaddadd': '3',
    'iaddsub': '3',
    'iaddmul': '3',
    'iadddiv': '3',
    'isubadd': '3',
    'isubsub': '3',
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
    'iadd': '2',
    'isub': '2',
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
# csv_title = ["HLC instruction", "YMC Address", "YMC assembly", "YMC encoding",
#              "Modified registers (if any, after execution)", "Modified flags (if any, after execution)"]
csv_title = ["HLC instruction", "YMC encoding",
             "Modified registers (if any, after execution)", "Modified flags (if any, after execution)", "YMC assembly", "YMC Address"]
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
    counter = 0
    # Start with 0. Mark it as 1 if found while. Until finished mark it as 0
    loop_flag = 0
    loop_jump_address = 0
    # Start with 0. Mark it as 1 if found while. Until finished mark it as 0
    if_jump_address = 0
    else_jump_address = 0
    if_flag = 0
    else_flag = 0
    while_cmp = ""
    while_instruction = ""
    while_start_address = 0
    counter_variable = 1
    lines = re.split(r'(?<!\\)\n', hlc_code)
    for line in lines:
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
                variable[var_name] = 0
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
                variable[var_name] = 0
                mapping[var_name] = "0" + str(counter_variable)
                counter_variable += 1
        elif line.startswith('print'):
            line_print = line.split()
            instruction = "call " + str(line_print[1])
            counter = generate_assembly_code("call", instruction, counter, line)
        elif line.startswith('if'):
            if if_flag == 1:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if_flag = 1
            if else_flag == 1:
                memory[int(else_jump_address)] = format(counter, '02x')
                else_flag = 0
            if loop_flag == 1:
                action_jump = while_instruction.split()[0]
                counter = generate_assembly_code(action_jump, while_instruction, counter, line)
                memory[int(loop_jump_address)] = format(counter, '02x')
                loop_flag = 0
            line_if = line.split()
            if len(line_if) == 4 and line_if[2] in relational_operators:
                # change when find the first end
                if_jump_address = counter + 4
                instruction = "cmp " + line_if[1] + " " + line_if[3]
                counter = generate_assembly_code("cmp", instruction, counter, line)
                if line_if[2] == relational_operators[0]:
                    instruction = "jge " + str(counter)
                    counter = generate_assembly_code("jge", instruction, counter, line)
                elif line_if[2] == relational_operators[1]:
                    instruction = "jg " + str(counter)
                    counter = generate_assembly_code("jg", instruction, counter, line)
                elif line_if[2] == relational_operators[2]:
                    instruction = "jle " + str(counter)
                    counter = generate_assembly_code("jle", instruction, counter, line)
                elif line_if[2] == relational_operators[3]:
                    instruction = "jl " + str(counter)
                    counter = generate_assembly_code("jl", instruction, counter, line)
                elif line_if[2] == relational_operators[4]:
                    instruction = "jne " + str(counter)
                    counter = generate_assembly_code("jne", instruction, counter, line)
                elif line_if[2] == relational_operators[5]:
                    instruction = "je " + str(counter)
                    counter = generate_assembly_code("je", instruction, counter, line)
            else:
                print("Error: Only one relational operator is allowed in if statements.")
                sys.exit()
        elif line.startswith('else'):
            if if_flag == 0:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if else_flag == 1:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if_flag = 0
            else_flag = 1
            line_else = line.split()
            if len(line_else) == 1:
                memory[int(if_jump_address)] = format((counter + 2), '02x')
                else_jump_address = counter + 1
                instruction = "jmp " + str(counter)
                counter = generate_assembly_code("jmp", instruction, counter, line)
            else:
                print("Error: Else statement is incorrect!")
                sys.exit()
        elif line.startswith('while'):
            if if_flag == 1:
                print("Error: If-else statement is incorrect!")
                sys.exit()
            if else_flag == 1:
                memory[int(else_jump_address)] = format(counter, '02x')
                else_flag = 0
            if loop_flag == 1:
                action_jump = while_instruction.split()[0]
                counter = generate_assembly_code(action_jump, while_instruction, counter, line)
                memory[int(loop_jump_address)] = format(counter, '02x')
                loop_flag = 0
            line_while = line.split()
            if len(line_while) == 4 and line_while[2] in relational_operators:
                while_start_address = counter
                loop_jump_address = counter + 4
                loop_flag = 1
                instruction = "cmp " + line_while[1] + " " + line_while[3]
                counter = generate_assembly_code("cmp", instruction, counter, line)
                if line_while[2] == relational_operators[0]:
                    instruction = "jge " + str(counter)
                    counter = generate_assembly_code("jge", instruction, counter, line)
                elif line_while[2] == relational_operators[1]:
                    instruction = "jg " + str(counter)
                    counter = generate_assembly_code("jg", instruction, counter, line)
                elif line_while[2] == relational_operators[2]:
                    instruction = "jle " + str(counter)
                    counter = generate_assembly_code("jle", instruction, counter, line)
                elif line_while[2] == relational_operators[3]:
                    instruction = "jl " + str(counter)
                    counter = generate_assembly_code("jl", instruction, counter, line)
                elif line_while[2] == relational_operators[4]:
                    instruction = "jne " + str(counter)
                    counter = generate_assembly_code("jne", instruction, counter, line)
                elif line_while[2] == relational_operators[5]:
                    instruction = "je " + str(counter)
                    counter = generate_assembly_code("je", instruction, counter, line)
                # change when find the first end
                while_instruction = "jmp " + str(while_start_address)
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
                                    instruction = "iaddadd ebx ecx"
                                    counter = generate_assembly_code("iaddadd", instruction, counter, line)
                                elif right_side[1] == operators[0] and right_side[3] == operators[1]:
                                    instruction = "iaddsub ebx ecx"
                                    counter = generate_assembly_code("iaddsub", instruction, counter, line)
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
                                    instruction = "isubadd ebx ecx"
                                    counter = generate_assembly_code("isubadd", instruction, counter, line)
                                elif right_side[1] == operators[1] and right_side[3] == operators[1]:
                                    instruction = "isubsub ebx ecx"
                                    counter = generate_assembly_code("isubsub", instruction, counter, line)
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
    if counter != 0:
        if if_flag == 1:
            print("Error: If-else statement is incorrect!")
            sys.exit()
        if else_flag == 1:
            memory[int(else_jump_address)] = format(counter, '02x')
        if loop_flag == 1:
            action_jump = while_instruction.split()[0]
            counter = generate_assembly_code(action_jump, while_instruction, counter, line)
            memory[int(loop_jump_address)] = format(counter, '02x')


def check_formula(expr):
    operator_count = sum(expr.count(op) for op in operators)
    if operator_count > 2:
        print("Error: The formula has more than 2 operators.")
        sys.exit()
    else:
        return expr.split()


def value_get_key(value_find, mapper_find):
    key_find = next((key for key, value in mapper_find.items() if value == value_find), None)
    return key_find


def save_csv_file(register_v, flag_v, hlc_code, memory_address, ymc_code, ymc_encoding):
    new_csv_line = [hlc_code, memory_address, ymc_code, ymc_encoding, register_v, flag_v]
    HLC_program.append(new_csv_line)


def generate_assembly_code(action, instruction, counter_c, hlc_code_line):
    counter_c = int(counter_c)
    if action == 'vrmov' or action == 'vmmov':
        counter_c = ymc_to_machine_value_left(instruction, counter_c, hlc_code_line)
    elif action == 'rmmov' or action == 'mrmov' or action == 'rrmov' or action == 'mmmov':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'cmp':
        counter_c = ymc_to_machine_value_right(instruction, counter_c, hlc_code_line)
    elif action == 'iaddadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'iaddsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'iaddmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'iadddiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'isubadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'isubsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'isubmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'isubdiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'imuladd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'imulsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'imulmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'imuldiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'idivadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'idivsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'idivmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'idivdiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'addadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'addsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'addmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'adddiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'subadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'subsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'submul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'subdiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'muladd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'mulsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'mulmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'muldiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'divadd':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'divsub':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'divmul':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'divdiv':
        counter_c = ymc_to_machine(instruction, counter_c, hlc_code_line)
    elif action == 'add':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'sub':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'mul':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'div':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'iadd':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'isub':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'imul':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'idiv':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    elif action == 'jmp':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'jle':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'jl':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'je':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'jne':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'jge':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'jg':
        counter_c = ymc_to_machine_short_value(instruction, counter_c, hlc_code_line)
    elif action == 'call':
        counter_c = ymc_to_machine_short(instruction, counter_c, hlc_code_line)
    else:
        print("Error: First part unknown action." + action)
        sys.exit()
    return counter_c


def ymc_to_machine(instruction_y2m, counter_y2m, hlc_code_line_y2m):
    instruction_y2m = instruction_y2m.strip()
    var_list = instruction_y2m.split()
    counter_y2m = insert_memory(ymc_to_machine_code.get(var_list[0]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    counter_y2m = insert_memory(mapping.get(var_list[1]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    counter_y2m = insert_memory(mapping.get(var_list[2]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    return counter_y2m


def ymc_to_machine_value_left(instruction_y2m, counter_y2m, hlc_code_line_y2m):
    instruction_y2m = instruction_y2m.strip()
    var_list = instruction_y2m.split()
    counter_y2m = insert_memory(ymc_to_machine_code.get(var_list[0]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    num = int(var_list[1])
    if num < 0:
        num = (1 << 8) + num
    hex_str = format(num, '02x')
    counter_y2m = insert_memory(hex_str, counter_y2m, instruction_y2m, hlc_code_line_y2m)
    counter_y2m = insert_memory(mapping.get(var_list[2]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    return counter_y2m


def ymc_to_machine_value_right(instruction_y2m, counter_y2m, hlc_code_line_y2m):
    instruction_y2m = instruction_y2m.strip()
    var_list = instruction_y2m.split()
    counter_y2m = insert_memory(ymc_to_machine_code.get(var_list[0]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    num = int(var_list[2])
    if num < 0:
        num = (1 << 8) + num
    hex_str = format(num, '02x')
    counter_y2m = insert_memory(mapping.get(var_list[1]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    counter_y2m = insert_memory(hex_str, counter_y2m, instruction_y2m, hlc_code_line_y2m)
    return counter_y2m


def ymc_to_machine_short(instruction_y2m, counter_y2m, hlc_code_line_y2m):
    instruction_y2m = instruction_y2m.strip()
    var_list = instruction_y2m.split()
    counter_y2m = insert_memory(ymc_to_machine_code.get(var_list[0]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    counter_y2m = insert_memory(mapping.get(var_list[1]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    return counter_y2m


def ymc_to_machine_short_value(instruction_y2m, counter_y2m, hlc_code_line_y2m):
    instruction_y2m = instruction_y2m.strip()
    var_list = instruction_y2m.split()
    counter_y2m = insert_memory(ymc_to_machine_code.get(var_list[0]), counter_y2m, instruction_y2m, hlc_code_line_y2m)
    num = int(var_list[1])
    if num < 0:
        num = (1 << 8) + num
    hex_str = format(num, '02x')
    counter_y2m = insert_memory(hex_str, counter_y2m, instruction_y2m, hlc_code_line_y2m)
    return counter_y2m


def insert_memory(machine_code, counter_memory, instruction_memory, hlc_code_line_memory):
    memory[counter_memory] = machine_code
    counter_memory += 1
    convert_hlc_ymc.append(instruction_memory)
    hlc_mapping_ymc.append(hlc_code_line_memory)
    return counter_memory


def process_memory_instruction(memory_instruction):
    pointer = 0
    while len(memory_instruction) > pointer:
        machine_code = memory_instruction[pointer]
        action = value_get_key(machine_code, ymc_to_machine_code)
        action_space = action_spaces.get(str(action), 'Unknown')
        if action_space == 'Unknown':
            print("End. The outer is above.")
            return
        action_space = int(action_space)
        action_start = pointer
        machine_code = str(machine_code)
        instruction = []
        while action_space > 1:
            pointer += 1
            action_space -= 1
            new_machine_code = memory_instruction[pointer]
            machine_code = machine_code + " " + str(new_machine_code)
            instruction.append(new_machine_code)
        pointer += 1
        pointer = process_function(action, instruction, pointer)
        registers_string = "eax=" + registers['eax'] +", ebx=" + registers['ebx'] +", ecx=" + registers['ecx'] +", edx="+ registers['edx']
        flags_string = "ZF=" + str(flags['ZF']) +", SF=" + str(flags['SF']) +", OF=" + str(flags['OF']) +", CF="+ str(flags['CF'])
        save_csv_file(hlc_mapping_ymc[action_start], action_start,
                      convert_hlc_ymc[action_start], machine_code, registers_string, flags_string)


def process_function(action, instruction, counter_c):
    if action == 'vrmov':
        value = format(int(instruction[0], 16), '02x')
        register = value_get_key(instruction[1], mapping)
        registers[register] = value
    elif action == 'vmmov':
        value = format(int(instruction[0], 16), '02x')
        variable_key = value_get_key(instruction[1], mapping)
        variable[variable_key] = value
    elif action == 'rmmov':
        register = value_get_key(instruction[0], mapping)
        value = registers[register]
        variable_key = value_get_key(instruction[1], mapping)
        variable[variable_key] = value
    elif action == 'mrmov':
        variable_key = value_get_key(instruction[0], mapping)
        value = variable[variable_key]
        register = value_get_key(instruction[1], mapping)
        registers[register] = value
    elif action == 'rrmov':
        register = value_get_key(instruction[0], mapping)
        value = registers[register]
        register = value_get_key(instruction[1], mapping)
        registers[register] = value
    elif action == 'mmmov':
        variable_key = value_get_key(instruction[0], mapping)
        value = variable[variable_key]
        variable_key = value_get_key(instruction[1], mapping)
        variable[variable_key] = value
    elif action == 'cmp':
        variable_key = value_get_key(instruction[0], mapping)
        value = int(str(variable[variable_key]), 16)
        cmp_value = int(instruction[1], 16)
        new_value = value - cmp_value
        if new_value == 0:
            flags['ZF'] = 1
        elif new_value > 0:
            flags['SF'] = 1
            flags['ZF'] = 0
        else:
            flags['SF'] = 0
            flags['ZF'] = 0
    elif action == 'iaddadd':
        registers['eax'] = operations('+', '+', instruction, 0)
    elif action == 'iaddsub':
        registers['eax'] = operations('+', '-', instruction, 0)
    elif action == 'iaddmul':
        registers['eax'] = operations('+', '*', instruction, 0)
    elif action == 'iadddiv':
        registers['eax'] = operations('+', '//', instruction, 0)
    elif action == 'isubadd':
        registers['eax'] = operations('-', '+', instruction, 0)
    elif action == 'isubsub':
        registers['eax'] = operations('-', '-', instruction, 0)
    elif action == 'isubmul':
        registers['eax'] = operations('-', '*', instruction, 0)
    elif action == 'isubdiv':
        registers['eax'] = operations('-', '/', instruction, 0)
    elif action == 'imuladd':
        registers['eax'] = operations('*', '+', instruction, 0)
    elif action == 'imulsub':
        registers['eax'] = operations('*', '-', instruction, 0)
    elif action == 'imulmul':
        registers['eax'] = operations('*', '*', instruction, 0)
    elif action == 'imuldiv':
        registers['eax'] = operations('*', '//', instruction, 0)
    elif action == 'idivadd':
        registers['eax'] = operations('//', '+', instruction, 0)
    elif action == 'idivsub':
        registers['eax'] = operations('//', '-', instruction, 0)
    elif action == 'idivmul':
        registers['eax'] = operations('//', '*', instruction, 0)
    elif action == 'idivdiv':
        registers['eax'] = operations('//', '//', instruction, 0)
    elif action == 'addadd':
        registers['eax'] = operations('+', '+', instruction, 1)
    elif action == 'addsub':
        registers['eax'] = operations('+', '-', instruction, 1)
    elif action == 'addmul':
        registers['eax'] = operations('+', '*', instruction, 1)
    elif action == 'adddiv':
        registers['eax'] = operations('+', '//', instruction, 1)
    elif action == 'subadd':
        registers['eax'] = operations('-', '+', instruction, 1)
    elif action == 'subsub':
        registers['eax'] = operations('-', '-', instruction, 1)
    elif action == 'submul':
        registers['eax'] = operations('-', '*', instruction, 1)
    elif action == 'subdiv':
        registers['eax'] = operations('-', '//', instruction, 1)
    elif action == 'muladd':
        registers['eax'] = operations('*', '+', instruction, 1)
    elif action == 'mulsub':
        registers['eax'] = operations('*', '-', instruction, 1)
    elif action == 'mulmul':
        registers['eax'] = operations('*', '*', instruction, 1)
    elif action == 'muldiv':
        registers['eax'] = operations('*', '//', instruction, 1)
    elif action == 'divadd':
        registers['eax'] = operations('//', '+', instruction, 1)
    elif action == 'divsub':
        registers['eax'] = operations('//', '-', instruction, 1)
    elif action == 'divmul':
        registers['eax'] = operations('//', '*', instruction, 1)
    elif action == 'divdiv':
        registers['eax'] = operations('//', '//', instruction, 1)
    elif action == 'add':
        registers['eax'] = operations('+', None, instruction, 1)
    elif action == 'sub':
        registers['eax'] = operations('-', None, instruction, 1)
    elif action == 'mul':
        registers['eax'] = operations('×', None, instruction, 1)
    elif action == 'div':
        registers['eax'] = operations('//', None, instruction, 1)
    elif action == 'iadd':
        registers['eax'] = operations('+', None, instruction, 0)
    elif action == 'isub':
        registers['eax'] = operations('-', None, instruction, 0)
    elif action == 'imul':
        registers['eax'] = operations('×', None, instruction, 0)
    elif action == 'idiv':
        registers['eax'] = operations('//', None, instruction, 0)
    elif action == 'jmp':
        counter_c = int(instruction[0], 16)
    elif action == 'jle':
        if flags['ZF'] == 1 or (flags['SF'] == 0 and flags['ZF'] == 0):
            counter_c = int(instruction[0], 16)
    elif action == 'jl':
        if flags['SF'] == 0 and flags['ZF'] == 0:
            counter_c = int(instruction[0], 16)
    elif action == 'je':
        if flags['ZF'] == 1:
            counter_c = int(instruction[0], 16)
    elif action == 'jne':
        if flags['ZF'] == 0:
            counter_c = int(instruction[0], 16)
    elif action == 'jge':
        if flags['ZF'] == 1 or (flags['SF'] == 1 and flags['ZF'] == 0):
            counter_c = int(instruction[0], 16)
    elif action == 'jg':
        if flags['SF'] == 1 and flags['ZF'] == 0:
            counter_c = int(instruction[0], 16)
    elif action == 'call':
        variable_key = value_get_key(instruction[0], mapping)
        if variable_key is not None:
            if variable_key != '\\n':
                print(int(str(variable[variable_key]), 16), end="")
                print(" ", end="")
            else:
                print('\n' + " ", end="")
        else:
            print('\n' + " ", end="")
    else:
        print("Error: Second part unknown action." + action)
        sys.exit()
    return counter_c


def operations(operator_1, operator_2, instruction, variable_type):
    flags['SF'] = 0
    flags['OF'] = 0
    flags['ZF'] = 0
    flags['CF'] = 0
    # variable_type: 0 signed, 1 unsigned
    if operator_2 is not None:
        value_1 = int(str(registers['eax']), 16)
        register_2 = value_get_key(instruction[0], mapping)
        value_2 = int(str(registers[register_2]), 16)
        register_3 = value_get_key(instruction[1], mapping)
        value_3 = int(str(registers[register_3]), 16)
        if variable_type == 1:
            value_1 = value_1 & 0xFF
            value_2 = value_2 & 0xFF
            value_3 = value_3 & 0xFF
        result = eval(f"{value_1} {operator_1} {value_2} {operator_2} {value_3}")
    else:
        value_1 = int(str(registers['eax']), 16)
        register_2 = value_get_key(instruction[0], mapping)
        value_2 = int(str(registers[register_2]), 16)
        if variable_type == 1:
            value_1 = value_1 & 0xFF
            value_2 = value_2 & 0xFF
        result = eval(f"{value_1} {operator_1} {value_2}")
    # Flags
    flags['SF'] = result < 0
    if variable_type == 0:
        max_value = 2 ** (8 * result.bit_length() - 1) - 1
        min_value = -max_value - 1
        flags['OF'] = result > max_value or result < min_value
    flags['ZF'] = result == 0
    flags['CF'] = result > 255
    if result < 0:
        result = (1 << 8) + result
    result = format(result, '02x')
    return result


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
