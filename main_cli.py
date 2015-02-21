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

    screen = curses.initscr()
    curses.noecho()
    curses.curs_set(0)
    screen.keypad(1)

    decoder = Decoder(get_config())        #Create the decoder from the config
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    stream.start_stream()


    decoder.start_utt()
    in_speech_bf = True         #Needed to get the state, when you are speaking/not speaking -> statusbar

    height, width = screen.getmaxyx()
    screen.addstr(0, 0, "Python PocketSphinx Speech Recognition (by matthiasjasny@gmail.com)")
    #screen.refresh()

    i = 0
    while True:
        screen.nodelay(1)
        event = screen.getch()
        if event == ord("q"): break

        buf = stream.read(1024)          #Read the first Chunk from the microphone
        if buf:
            #Pass the Chunk to the decoder
            screen.addstr(height-2, 0, "Decoded chunks: "+str(i))
            i+=1

            decoder.process_raw(buf, False, False)
            try:
                #If the decoder has partial results, display them in the GUI.
                if  decoder.hyp().hypstr != '':
                    hypstr = decoder.hyp().hypstr
                    #print('Partial decoding result: '+ hypstr)
                    screen.addstr(3, 0, ' '*(width-1))
                    screen.addstr(3, 0,'Partial decoding result: '+ hypstr)
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
                            screen.addstr(6, 0, ' '*(width-1))
                            screen.addstr(6, 0, 'Stream decoding result: '+ decoded_string)

                    except AttributeError:
                        pass
                    decoder.start_utt()            #Say to the decoder, that a new "sentence" begins
                    screen.addstr(height-1, 0, ' '*(width-1))
                    screen.addstr(height-1, 0, "Listening: No audio")
                    #print("stopped listenning")
                else:
                    screen.addstr(height-1, 0, ' '*(width-1))
                    screen.addstr(height-1, 0, "Listening: Incoming audio...")
                    #print("start listening")

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
