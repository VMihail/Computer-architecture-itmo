import string

OperationCodes = {'0110011': 'r',
                  '0010011': 'i',
                  '0100011': 's',
                  '1100011': 'b',
                  '0000011': 'l',
                  '1101111': 'j',
                  '1100111': 'ja'}

RInst = {('0000000', '000'): 'add   ',
         ('0100000', '000'): 'sub   ',
         ('0000000', '001'): 'sll   ',
         ('0000000', '010'): 'slt   ',
         ('0000000', '011'): 'sltu  ',
         ('0000000', '100'): 'xor   ',
         ('0000000', '101'): 'srl   ',
         ('0100000', '101'): 'sra   ',
         ('0000000', '110'): 'or    ',
         ('0000000', '111'): 'and   ',
         ('0000001', '000'): 'mul   ',
         ('0000001', '001'): 'mulh  ',
         ('0000001', '010'): 'mulhsu',
         ('0000001', '011'): 'mulhu ',
         ('0000001', '100'): 'div   ',
         ('0000001', '101'): 'divu  ',
         ('0000001', '110'): 'rem   ',
         ('0000001', '111'): 'remu  '}

IInst = {'000': 'addi  ',
         '001': 'slli  ',
         '010': 'slti  ',
         '011': 'sltiu ',
         '100': 'xori  ',
         '101': 'sr_   ',
         '110': 'ori   ',
         '111': 'andi  '}

SInst = {'000': 'sb    ',
         '001': 'sh    ',
         '010': 'sw    '}

BInst = {'000': 'beq   ',
         '001': 'bne   ',
         '100': 'blt   ',
         '101': 'bge   ',
         '110': 'bltu  ',
         '111': 'bgeu  '}

LInst = {'000': 'lb    ',
         '001': 'lh    ',
         '010': 'lw    ',
         '100': 'lbu   ',
         '101': 'lhu   '}


def reverse(value: string) -> int:
    return value[6:8] + value[4:6] + value[2:4] + value[0:2]


def fillWithZeroes(index: string) -> string:
    return '0' * (8 - len(index)) + index


def translate(a):
    if a[0] == '1':
        return int(a[1:], 2) - int(a[:1]) * (2 ** (len(a) - 1))
    return int(a, 2)


def getTableAddress(buffer, isLittle):
    """ смещение заголовков секций от начала файла или адрес в файле """
    address = ''
    for byte in buffer[32:34]:
        if isLittle:
            #  кодирование от младшего к старшему при little
            address = hex(byte)[2::] + address
        else:
            # наоборот, если big
            address += hex(byte)[2::]
    return int(address, 16)


def isLittleEndian(buffer):
    """
    :param buffer:
    :return: little endian или big endian
    """
    return hex(buffer[5]) == '0x1'


def binText(buffer, textSize, textAddress, littleEndian):
    """
    :param littleEndian:
    :param buffer:
    :param textSize:
    :param textAddress:
    :return: text в двоичной системе
    """
    command = ''
    textBin = list()
    ind = 1
    index = 0
    for byte in buffer[textAddress: textAddress + textSize]:
        now = bin(byte)[2:]
        while len(now) < 8:
            now = '0' + now
        if littleEndian:
            command = now + command
        else:
            command += now
        if ind % 4 == 0:
            textBin.append([command, index])
            command = ''
            index += 4
        ind += 1
    return textBin


def getText(buffer, tableAddress, littleEndian):
    """ находим адрес .text и .symtab
        создаем строки для считывания """
    ind = 1
    textAddress = textSize = section = ''
    for byte in buffer[tableAddress::]:
        now = hex(byte)[2::]
        while len(now) < 2:
            now = '0' + now
        section += now
        if ind % 40 == 0:
            sectionType = section[8:16]
            sectionFlags = section[16:24]
            if littleEndian:
                sectionType = reverse(sectionType)
                sectionFlags = reverse(sectionFlags)
            sectionType = int(sectionType, 16)
            sectionFlags = int(sectionFlags, 16)
            if sectionType == 1 and sectionFlags == 6:
                textAddress = section[32:40]
                textSize = section[40:48]
            section = ''
        ind += 1
    if littleEndian:
        textAddress = reverse(textAddress)
        textSize = reverse(textSize)
    textAddress = int(textAddress, 16)
    textSize = int(textSize, 16)
    return textAddress, textSize


class OperationsHandler:
    def __init__(self):
        self.n_number = 0
        self.p_number = -1

    def apply(self, word) -> None:
        instruction = word[0]
        index = word[1]
        index = fillWithZeroes(hex(index)[2::])
        opCd = instruction[25:32]
        rs1 = translate(instruction[12:17])
        rs2 = translate(instruction[7:12])
        rd = translate(instruction[20:25])
        if OperationCodes[opCd] == 'r':
            func = (instruction[0:7], instruction[17:20])
            print(index, ':', ' ' * 8, RInst[func],
                  ' ' * 4, 'a', rd, ', ', 'a',
                  rs1, ', ', 'a', rs2,
                  sep='')
        elif OperationCodes[opCd] == 'i':
            imm = translate(instruction[0:12])
            func = instruction[17:20]
            zero = 'zero' if rs1 == 0 else 'a' + str(rs1)
            if self.p_number == -1:
                print(index, ':', '<main>  ', IInst[func],
                      ' ' * 4, 'a', rd, ', ',
                      zero, ', ', imm,
                      sep='')
                self.p_number = 0
            else:
                print(index, ':', ' ' * 8, IInst[func],
                      ' ' * 4, 'a', rd, ', ',
                      zero, ', ',
                      imm,
                      sep='')
        elif OperationCodes[opCd] == 's':
            imm = translate(instruction[0:7] + instruction[20:25])
            func = instruction[17:20]
            print(index, ':', ' ' * 8, SInst[func],
                  ' ' * 4, 'a', rs1, ', ',
                  imm, '(a', rs2, ')',
                  sep='')
        elif OperationCodes[opCd] == 'j':
            imm = instruction[0:20]
            imm = translate(imm)
            zero = 'zero' if rd == 0 else 'a' + str(rd)
            print(index, ':', ' ' * 8, 'jal   ',
                  ' ' * 4, zero, ', ',
                  imm,
                  sep='')
            self.n_number += 1
        elif OperationCodes[opCd] == 'ja':
            imm = instruction[0:12]
            imm = translate(imm)
            print(index, ':', ' ' * 8, 'jalr  ',
                  ' ' * 4, 'a', rd, ', ', 'a',
                  rs1, ', ', imm,
                  sep='')
        elif OperationCodes[opCd] == 'l':
            imm = instruction[0:12]
            imm = translate(imm)
            func = instruction[17:20]
            if LInst[func] == 'lw    ' and (self.n_number != self.p_number):
                print(index, ':', '<.LBB0_',
                      self.n_number, '>', LInst[func],
                      ' ' * 4, 'a', rd, ', ',
                      imm, '(a', rs1, ')',
                      sep='')
                self.p_number = self.n_number
            else:
                print(index, ':', ' ' * 8, LInst[func],
                      ' ' * 4, 'a', rd, ', ', imm,
                      '(a', rs1, ')',
                      sep='')
        elif OperationCodes[opCd] == 'b':
            func = instruction[17:20]
            imm = instruction[0:7] + instruction[20:25]
            imm = translate(imm)
            zero = 'zero' if rs1 == 0 else 'a' + str(rs1)
            print(index, ':', ' ' * 8, BInst[func],
                  ' ' * 4, 'a', rd, ', ',
                  zero, ', ', imm,
                  sep='')

