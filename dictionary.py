#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import fcntl, termios, struct


def getTerminalSize():
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])

def main():
    dic = 'voxforge-de-r20140813/etc/voxforge.dic_backup'

    (width, height) = getTerminalSize()
    hash_line = ''
    for i in range(0, width):
        hash_line += '#'

    with open(dic, 'r') as f:
        lines = f.readlines()

    #third = list(set(first) | set(second))   

    words = raw_input("Please enter words to look up: > ").upper().split(' ')

    dic_words = []
    phenomes = []
    for line in lines:
        _line = line.strip().split(' ')
        dic_words.append(_line[0])
        _line.pop(0)
        phenomes.append(' '.join(_line))

    for word in words:
        if word in dic_words:
            print '! ' + word + ' | ' + phenomes[dic_words.index(word)]
        else:
            for _word in dic_words:
                if word in _word:
                    index = dic_words.index(_word)
                    print word + ' | ' + dic_words[index] +' | ' + phenomes[index]
        print hash_line

if __name__ == '__main__':
    main()
