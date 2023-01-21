from operations import *


class RuntimeException(Exception):
    def __init__(self, txt):
        self.txt = txt


def main():
    inputFile = open('./venv/bin/test_elf (1).file', 'rb')
    try:
        buffer = inputFile.read()
    except IOError:
        raise RuntimeException('Файл не найден')
    inputFile.close()
    # проверка на 64-битные файлы
    if hex(buffer[4]) != '0x1':
        raise RuntimeException('не поддерживается')
    littleEndian = isLittleEndian(buffer)
    tableAddress = getTableAddress(buffer, littleEndian)
    textAddress, textSize = getText(buffer, tableAddress, littleEndian)
    text = binText(buffer, textSize, textAddress, littleEndian)
    handler = OperationsHandler()
    for word in text:
        handler.apply(word)


if __name__ == '__main__':
    main()
