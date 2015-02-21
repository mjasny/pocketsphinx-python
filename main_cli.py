#!/usr/bin/env python2
#-*- coding: utf-8 -*-


import curses
import pyaudio

import subprocess

from pocketsphinx import *
from sphinxbase import *

hmm= 'voxforge-de-r20141117/model_parameters/voxforge.cd_cont_3000/'
lm = 'voxforge-de-r20141117/etc/voxforge.lm.DMP'
dic = 'voxforge-de-r20141117/etc/voxforge.dic'

def get_config():
    #Create a config object for the Decoder, which will later decode our spoken words.
    config = Decoder.default_config()
    config.set_string('-hmm', hmm)
    config.set_string('-lm', lm)
    config.set_string('-dict', dic)
    #Uncomment the following if you want to log only errors.
    config.set_string('-logfn', '/dev/null')

    return config


def main():


    decoder = Decoder(get_config())        #Create the decoder from the config
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    stream.start_stream()


    decoder.start_utt()
    in_speech_bf = True         #Needed to get the state, when you are speaking/not speaking -> statusbar

    screen = curses.initscr()
    curses.noecho()
    curses.curs_set(0)
    screen.keypad(1)

    height, width = screen.getmaxyx()

    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.use_default_colors()



    _str = "Python PocketSphinx Speech Recognition (by matthiasjasny@gmail.com)"
    _remain = width-len(_str)
    _l = _remain/2
    _r = _remain-_l
    screen.addstr(0, 0,' '*(_r)+ _str+' '*(_l), curses.color_pair(1))

    screen.addstr(2, 0, "Partial decoding result:")

    _pl = (height)/2+1
    screen.addstr(_pl-1, 0, 'Stream decoding result:')
    #screen.refresh()

    i = 0
    while True:
        screen.nodelay(1)
        event = screen.getch()
        if event == ord("q"): break

        buf = stream.read(1024)          #Read the first Chunk from the microphone
        if buf:
            #Pass the Chunk to the decoder
            _str = "Decoded chunks: "+str(i)
            _remain = width-len(_str)
            screen.addstr(height-2, 0, _str +' '*_remain, curses.color_pair(2))
            i+=1

            decoder.process_raw(buf, False, False)
            try:
                #If the decoder has partial results, display them in the GUI.
                if  decoder.hyp().hypstr != '':
                    hypstr = decoder.hyp().hypstr
                    #print('Partial decoding result: '+ hypstr)
                    screen.addstr(3, 0, ' '*(width-1))
                    screen.addstr(3, 0, hypstr)
            except AttributeError:
                pass
            if decoder.get_in_speech():
                pass
                #sys.stdout.write('.')
                #sys.stdout.flush()
            if decoder.get_in_speech() != in_speech_bf:
                in_speech_bf = decoder.get_in_speech()
                #When the speech ends:
                if not in_speech_bf:
                    decoder.end_utt()
                    try:
                        #Since the speech is ended, we can assume that we have final results, then display them
                        if decoder.hyp().hypstr != '':
                            decoded_string = decoder.hyp().hypstr
                            screen.addstr(_pl, 0, ' '*(width-1))
                            screen.addstr(_pl, 0, decoded_string)

                    except AttributeError:
                        pass
                    decoder.start_utt()            #Say to the decoder, that a new "sentence" begins

                    _str = "Listening: No audio"
                    _remain = width-len(_str)-1
                    screen.addstr(height-1, 0, _str+' '*(_remain), curses.color_pair(2))
                    screen.insstr(height-1, width-1, ' ', curses.color_pair(2))

                    #print("stopped listenning")
                else:
                    _str = "Listening: Incoming audio..."
                    _remain = width-len(_str)-1
                    screen.addstr(height-1, 0, _str+' '*(_remain), curses.color_pair(2))
                    screen.insstr(height-1, width-1, ' ', curses.color_pair(2))

            screen.refresh()
        else:
            break

    '''
    while True:
        event = screen.getch()
        if event == ord("q"): break
        elif event == curses.KEY_UP:
            screen.clear()
            screen.addstr("The User Pressed UP")
        elif event == curses.KEY_DOWN:
            screen.clear()
            screen.addstr("The User Pressed DOWN")
    '''

    curses.initscr()
    curses.nocbreak()
    curses.echo()
    curses.endwin()


if __name__ == '__main__':
    main()
