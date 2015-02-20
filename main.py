#!/usr/bin/env python2
# -*- coding: utf-8 -*-

##############################################
#title           :main.py
#description     :Voice recognition via pocketsphinx in python
#description     :Spracherkennung über pocketsphinx in python
#authors         :Matthias Ja. (http://youtube.com/Mattze96)
#date            :20140923
#version         :0.1
#usage           :python main.py
#python_version  :2.7.8
##############################################

#Tutorial zu/for pocketsphinx-python:
#https://mattze96.safe-ws.de/blog/?p=640

#German voice-model/Deutsches Sprachmodell: 
#http://goofy.zamia.org/voxforge/de/voxforge-de-r20140813.tgz

#Additional Libraries/Zusätzliche Bibliotheken
#https://github.com/cmusphinx/sphinxbase
#https://github.com/cmusphinx/pocketsphinx
#https://github.com/cmusphinx/sphinxtrain (only needed for model-adaption)

#Youtube Demo-Videos: (german/deutsch)
#https://www.youtube.com/watch?v=EcAt-ZhRPBw   (Version 1)
#https://www.youtube.com/watch?v=dIUqUwZPMc4   (Version 2)

##############################################
#Note:
#The following code is only commented in english. If you have questions
#fell free to contact me at: matthiasjasny@gmail.com

#Der nachfolgende Quellcode ist nur in english kommentiert. Wenn Sie/Du Fragen
#hast, schreibe mir einfach eine Mail: matthiasjasny@gmail.com

##############################################
#ToDo:
#More automatic model-adaption (start the record if the user starts to speak)
#Command support: Computer lights on. Open Webbrowser. etc.

##############################################
#Changelog:
#todo :)
##############################################

from array import array
from struct import pack
import sys, os
import time
import pyaudio
import wave
import gobject
import subprocess
import contextlib
import threading

import pygtk
pygtk.require("2.0")
import gtk

##############################################
#Please compile from the git-repository
from pocketsphinx import *
from sphinxbase import *
##############################################


#Use created adaptions if available
use_adaption_data = True


#Specifiy here the required paths for the language model
hmm= 'voxforge-de-r20141117/model_parameters/voxforge.cd_cont_3000/'
lm = 'voxforge-de-r20141117/etc/voxforge.lm.DMP'
dic = 'voxforge-de-r20141117/etc/voxforge.dic'

#Path of programs used by the model-adaption
#To find out use the "whereis program" command
sphinx_fe = "/usr/bin/sphinx_fe"
pocketsphinx_mdef_convert = "/usr/bin/pocketsphinx_mdef_convert"
bw = "/usr/local/libexec/sphinxtrain/bw"
mllr_solve = "/usr/local/libexec/sphinxtrain/mllr_solve"

#Specify the path, where the files for the model-generation are stored.
working_dir = "model_generation/"


def unbuffered(proc, stream='stdout'):
    '''Used to get unbuffered output from the commands run by the model-adaption'''
    newlines = ['\n', '\r\n', '\r']
    stream = getattr(proc, stream)
    with contextlib.closing(stream):
        while True:
            out = []
            last = stream.read(1)
            if last == '' and proc.poll() is not None:
                break
            while last not in newlines:
                if last == '' and proc.poll() is not None:
                    break
                out.append(last)
                last = stream.read(1)
            out = ''.join(out)
            yield out

class Base:
    class ModelAdaption(threading.Thread):
        '''Class for the model-adaption. Threadable.'''
        def __init__(self, name, sentences):
            threading.Thread.__init__(self)
            self.name = name
            self.sentences = sentences
            self.running = True

        def run(self):
            '''Is called when thread.start is run.'''
            #Create a pyaudio stream to later record from the microphone
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)

            count = 1                   #Used for training-file naming
            ma_colorbutton.show()

            filename = 'training'       #specify filename: training_1.wav; training_2.wav....

            if not os.path.exists(working_dir):
                os.mkdir(working_dir)

            #Go trough every sentence from the textfile, whose sentences are stored in the list self.sentences
            for sentence in self.sentences:
                gtk.gdk.threads_enter()
                ma_info_textbuffer.set_text("You have to read the following sentence.")
                ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "Click on the button. Start reading, if the button gets green. ")
                ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "If you are ready wait 1 second and click the button again.\n\n")
                gtk.gdk.threads_leave()
                print(sentence.strip())
                ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), sentence.strip())
                global ma_is_clicked
                ma_is_clicked = False
                
                #Wait for the initial click of the "record" button
                while not ma_is_clicked and self.running:
                    time.sleep(0.2)
                if not self.running:
                    return

                #change the color from red to green, so that the user knows, when to start speak
                map = ma_colorbutton.get_colormap()
                color = map.alloc_color("red")
                style = ma_colorbutton.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = color
                style.bg[gtk.STATE_PRELIGHT] = color
                ma_colorbutton.set_style(style)
                time.sleep(1)
                map = ma_colorbutton.get_colormap()
                color = map.alloc_color("green")
                style = ma_colorbutton.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = color
                style.bg[gtk.STATE_PRELIGHT] = color
                ma_colorbutton.set_style(style)


                #create a array to store the data from the stream and write it later to a .wav file
                data_all = array('h')
                ma_is_clicked = False
                stream.start_stream()            #Start the pyaudio recording stream
                #While the model-adaption thread is running and no button is clicked: record sound.
                while self.running and not ma_is_clicked:
                    buf = stream.read(1024)           #read first chunk from the mic-stream
                    if buf:
                        data_chunk = array('h', buf)
                        percent = max(data_chunk)/1000.
                        if percent > 1.0:
                            percent = 1.0
                        #We have to do the following, because we are not in the main thread and want to
                        #modify the value of a progressbar
                        gtk.gdk.threads_enter()         
                        ma_level_progressbar.set_fraction(percent) #Set "level" of the progressbar, which indicates the input volume
                        gtk.gdk.threads_leave()
                        data_all.extend(data_chunk)
                    else:
                        break
                        
                #Stop the recording stream
                stream.stop_stream()

                #filename = self.name.split('/')[len(self.name.split('/'))-1][:-4]
                #filename = filename

                #After recording save the data to the wav-file.
                wf = wave.open(working_dir+filename+'_'+str(count)+'.wav', 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                data_all = pack('<' + ('h' * len(data_all)), *data_all)
                wf.writeframes(data_all)
                wf.close()

                #Now write the filename from above into .fileids and the sentence into transcription.
                #The following two files are used by the model-adaption, we do later after recording all sentences.
                with open(working_dir+filename+".fileids", "a") as f:
                    f.write(working_dir+filename+'_'+str(count)+'\n')
                with open(working_dir+filename+".transcription", "a") as f:
                    line = unicode(sentence).strip().upper()
                    line = "".join(c for c in line if c not in ('!', '.' ,':', ';', ',', '?'))
                    f.write('<s> '+line+' </s> ('+working_dir+filename+'_'+str(count)+')\n')

                count+=1    #Increase the counter for the filenames
                #Set the recording button to the "normal" state
                map = ma_colorbutton.get_colormap()
                color = map.alloc_color("white")
                style = ma_colorbutton.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = color
                style.bg[gtk.STATE_PRELIGHT] = color
                ma_colorbutton.set_style(style)

            #Close the thread and terminate the pyaudio object. We don't need them anymore, because all sentences are already recorded
            stream.close()
            p.terminate()

            gtk.gdk.threads_enter()       #Again: needed, because we modify the GUI.
            ma_info_textbuffer.set_text("Now you have recorded all training data.\n\n")
            ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "In the next seconds i'm trying to adapt it to the new model. ")
            gtk.gdk.threads_leave()

            def run_command(cmd):
                '''Run the model-adaption commands and display the output in realtime to the GUI and console-log'''
                print(' '.join(cmd))
                proc = subprocess.Popen(cmd,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        universal_newlines=True,)

                for line in unbuffered(proc):
                    print(line)
                    ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), line+'\n')


            gtk.gdk.threads_enter()
            run_command(cmd = [sphinx_fe, '-argfile', hmm+'feat.params', '-samprate', '16000', '-c', working_dir+filename+'.fileids', '-di', '.',
                '-do', '.', '-ei', 'wav', '-eo', 'mfc', '-mswav', 'yes'])
            ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "\n\nNext: Convert mdef to mdef.txt")
            gtk.gdk.threads_leave()

            time.sleep(3)        #We don't need the breaks here, but it is easier to follow all steps of adaption
            gtk.gdk.threads_enter()
            run_command(cmd = [pocketsphinx_mdef_convert, '-text', hmm+'mdef', working_dir+'mdef.txt'])
            ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "\n\nNext: Run bw")
            gtk.gdk.threads_leave()

            time.sleep(3)
            gtk.gdk.threads_enter()
            run_command(cmd = [bw, '-hmmdir', hmm, '-moddeffn', working_dir+'mdef.txt', '-ts2cbfn', '.cont.',
                '-feat', '1s_c_d_dd', '-cmn', 'current', '-agc', 'none', '-dictfn', dic, '-ctlfn', working_dir+filename+'.fileids',
                '-lsnfn', working_dir+filename+'.transcription', '-lda', hmm+'feature_transform', '-accumdir', working_dir])
            ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "\n\nNext: Run mllr_solve")
            gtk.gdk.threads_leave()

            time.sleep(3)
            gtk.gdk.threads_enter()
            run_command(cmd = [mllr_solve, '-meanfn', hmm+'means', '-varfn', hmm+'variances', '-outmllrfn', working_dir+'mllr_matrix', '-accumdir', working_dir])
            ma_info_textbuffer.insert(ma_info_textbuffer.get_end_iter(), "\n\nReady!! Check log for errors or warnings.")
            gtk.gdk.threads_leave()

            print("MA  is over.")


        def stop(self):
            '''Is called when the thread should terminate/stop'''
            self.running = False

    class ConsoleOutput:
        '''We use this class to redirect the console output to the debug-tab in the GUI.'''
        def __init__(self, source):
            self.source=source
            self.buf = []

        def update_buffer(self):
            gtk.gdk.threads_enter()
            textbuffer_output.insert(textbuffer_output.get_end_iter(), ''.join(self.buf))
            gtk.gdk.threads_leave()
            self.buf = []

        def write(self, data):
            stdout_old.write(data)
            self.buf.append(data)
            if data.endswith('\n'):
                gobject.idle_add(self.update_buffer)

        def __del__(self):
            if self.buf != []:
                gobject.idle_add(self.update_buffer)

    class PocketSphinx(threading.Thread):
        '''Class for the first tab in the GUI.
           This is the most important part, because the recognition is done here.        
        '''
        def __init__ (self):
            threading.Thread.__init__(self)

        def get_config(self):
            #Create a config object for the Decoder, which will later decode our spoken words.
            config = Decoder.default_config()
            config.set_string('-hmm', hmm)
            config.set_string('-lm', lm)
            config.set_string('-dict', dic)
            #Uncomment the following if you want to log only errors.
            #config.set_string('-logfn', '/dev/null')
            if use_adaption_data:
                if os.path.isfile(working_dir+"mllr_matrix"):
                    print("Trainingdata exists")
                    #config.set_string('-mllr', working_dir+"mllr_matrix")
                else:
                    print("Trainingdata does not exist.")

            return config

        def run(self):
            print ("Run")
            self.running = True

            decoder = Decoder(self.get_config())        #Create the decoder from the config
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
            stream.start_stream()

            in_speech_bf = True         #Needed to get the state, when you are speaking/not speaking -> statusbar
            decoder.start_utt()


            while self.running:
                buf = stream.read(1024)          #Read the first Chunk from the microphone
                if buf:
                    #Pass the Chunk to the decoder
                    decoder.process_raw(buf, False, False)
                    try:
                        #If the decoder has partial results, display them in the GUI.
                        if  decoder.hyp().hypstr != '':
                            hypstr = decoder.hyp().hypstr
                            print('Partial decoding result: '+ hypstr)
                            if textbuffer_partial.get_text(*textbuffer_partial.get_bounds()) != hypstr:
                                gtk.gdk.threads_enter()
                                textbuffer_partial.set_text(hypstr)
                                gtk.gdk.threads_leave()
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
                                    print('Stream decoding result: '+ decoded_string)
                                    gtk.gdk.threads_enter()
                                    textbuffer_end.insert( textbuffer_end.get_end_iter(), decoded_string+"\n")
                                    gtk.gdk.threads_leave()
                            except AttributeError:
                                pass
                            decoder.start_utt()            #Say to the decoder, that a new "sentence" begins
                            gtk.gdk.threads_enter()
                            statusbar.push(0, "Listening: No audio")
                            gtk.gdk.threads_leave()
                            print("stopped listenning")
                        else:
                            gtk.gdk.threads_enter()
                            statusbar.push(0, "Listening: Incoming audio...")
                            gtk.gdk.threads_leave()
                            print("start listening")
                else:
                    break
                #print decoder.get_in_speech()
                
            #We get here, out of the while loop, if the user aborts the recognition thread.
            decoder.end_utt()
            print("PS  is over.")
            #Do some cleanup
            stream.stop_stream()
            stream.close()
            p.terminate()

        def stop(self):
            #Is called, when the user terminates/stops the recognition thread
            print ("Received stop-signal, please wait until PS gets closed.")
            self.running = False


    def ma_is_clicked_button(self, widget):
        '''Called as a onclick function by the record-button in the model-adaption tab'''
        global ma_is_clicked
        ma_is_clicked = True

    def destroy(self, widget, data=None):
        '''Called when the user closes the GUI. Used to do cleanup.'''
        print("Got destroy()")
        sys.stdout = stdout_old
        #sys.stderr = stderr_old
        self.stop_ps(widget)
        self.stop_ma(widget)
        gtk.main_quit()

    def start_ps(self, widget):
        '''Called by the gui button, starts the recognition thread'''
        print("Got start_ps()")
        if 'ps' not in my_threads:
            self.ps = self.PocketSphinx()
            self.ps.start()
            my_threads.append("ps")
            print("Gestartet")
        else:
            print("Running right now")

    def stop_ps(self, widget):
        '''Called by the gui button, stops the recognition thread'''
        try:
            self.ps.stop()
            my_threads.remove('ps')
            statusbar.push(0, "Not Listening.")
        except AttributeError:
            pass
        except ValueError:
            pass
        print("Got stop_ps()")

    def start_ma(self, widget):
        '''Called by the gui button, starts the model-adaption thread'''
        #filename = "foo"
        #Get the filename of the file containg the training sentences, via a filechooser dialog.
        filename = self.ma_textfile_select()
        if filename == None:
            print("Nothing selected")
            ma_info_textbuffer.set_text("You canceled the filechooser dialog. To restart, click on start.")
            return

        #Save the sentences to a list
        try:
            with open(filename) as f:
                sentences = f.readlines()
        except IOError:
            sentences = []

        print(sentences)

        print("Got start_ma()")
        #Check if running, start the thread.
        if 'ma' not in my_threads:
            self.ma = self.ModelAdaption(filename, sentences)
            self.ma.start()
            my_threads.append("ma")
            print("Gestartet")
        else:
            print("Running right now")

    def stop_ma(self, widget):
        '''Called by the gui button, stops the model-adaption thread'''
        try:
            self.ma.stop()
            my_threads.remove('ma')
        except AttributeError:
            pass
        except ValueError:
            pass
        print("Got stop_ma()")

    def _autoscroll(self, *args):
        '''Used for the textfields and do automatic scroll down.'''
        adj = args[0].get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def ma_textfile_select(self):
        '''File selector dialog.'''
        dialog = gtk.FileChooserDialog("Open Textfile...",
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        filter = gtk.FileFilter()
        filter.set_name("Textfiles")
        filter.add_mime_type("text/plain")
        filter.add_pattern("*.txt")
        dialog.add_filter(filter)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            filename = dialog.get_filename()
            print(filename+ ' selected')
            dialog.destroy()
            return filename
        elif response == gtk.RESPONSE_CANCEL:
            print('Closed, no files selected')
            dialog.destroy()
            return None



    def __init__(self):
        '''Init the GUI and everything else'''
        global stdout_old
        stdout_old = sys.stdout        #"Backup" the old sys.stdout
        global my_threads
        my_threads = []
        #global stderr_old
        #stderr_old = sys.stderr
        sys.stdout = self.ConsoleOutput(None)     #"Redirect output to the debug tab"
        #sys.stderr = self.ConsoleOutput(None)

        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_position(gtk.WIN_POS_CENTER)     #POS_CENTER , MOUSE
        window.set_keep_above(True);
        window.set_size_request(640, 480)
        window.set_title("PocketSphinx Speech Recogntition (by matthiasjasny@gmail.com)")
        #self.window.set_tooltip_text("foo")

        file_menu = gtk.Menu()

        # Create the menubar and its items
        mb = gtk.MenuBar()

        filemenu = gtk.Menu()
        filem = gtk.MenuItem("File")
        filem.set_submenu(filemenu)

        exit = gtk.MenuItem("Exit")
        exit.connect("activate", gtk.main_quit)
        filemenu.append(exit)

        mb.append(filem)

        vbox = gtk.VBox(False, 0)
        vbox.pack_start(mb, False, False, 0)

        mb.show()
        filem.show()
        exit.show()

        #Vertical box for the pocketsphinx recognition tab
        ps_vbox = gtk.VBox(False, 0)

        label = gtk.Label("Partial results:")
        ps_vbox.pack_start(label, False, False, 0)
        label.show()

        #Textfield for partial results
        self.sw_partial = gtk.ScrolledWindow()
        self.sw_partial.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        textview_partial= gtk.TextView()
        textview_partial.set_editable(False)
        textview_partial.set_wrap_mode(gtk.WRAP_WORD) #WRAP_WORD WRAP_CHAR
        textview_partial.connect("size-allocate", self._autoscroll, self.sw_partial)
        global textbuffer_partial
        textbuffer_partial = textview_partial.get_buffer()
        self.sw_partial.add(textview_partial)
        textview_partial.show()
        self.sw_partial.set_size_request(-1, 150)
        self.sw_partial.show()

        ps_vbox.pack_start(self.sw_partial, False, False, 0)

        label = gtk.Label("End results:")
        ps_vbox.pack_start(label, False, False, 0)
        label.show()

        #Textfield for final results
        self.sw_end = gtk.ScrolledWindow()
        self.sw_end.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        textview_end= gtk.TextView()
        textview_end.set_editable(False)
        textview_end.set_wrap_mode(gtk.WRAP_WORD) #WRAP_WORD WRAP_CHAR
        textview_end.connect("size-allocate", self._autoscroll, self.sw_end)
        global textbuffer_end
        textbuffer_end = textview_end.get_buffer()
        self.sw_end.add(textview_end)
        textview_end.show()
        self.sw_end.set_size_request(-1, 150)
        self.sw_end.show()

        ps_vbox.pack_start(self.sw_end, False, False, 0)


        #Create button to start/stop the recognition
        self.ps_fixed = gtk.Fixed()
        self.button1 = gtk.Button("Start pocketsphinx")
        self.button1.connect("clicked", self.start_ps)
        self.button1.set_tooltip_text("This button will close this window")
        self.button1.show()
        self.ps_fixed.put(self.button1, 0, 10)

        self.button2 = gtk.Button("Stop pocketsphinx")
        self.button2.connect("clicked", self.stop_ps)
        self.button2.show()
        self.ps_fixed.put(self.button2, 140, 10)

        self.ps_fixed.show()

        ps_vbox.pack_start(self.ps_fixed, False, False, 0)
        ps_vbox.show()
        #fixed.put(self.sw, 0, 200)
        #self.ps_table_layout.show()

        #Horizontal box for the model-adaption tab
        self.ma_hbox = gtk.HBox(False, 0)
        global ma_level_progressbar
        ma_level_progressbar = gtk.ProgressBar(adjustment=None)
        ma_level_progressbar.set_fraction(0)
        ma_level_progressbar.set_orientation(gtk.PROGRESS_BOTTOM_TO_TOP)
        ma_level_progressbar.show()

        #Progressbar for indication the microphone input volume
        self.ma_hbox.pack_start(ma_level_progressbar, False, False, 0)
        self.ma_hbox.show()

        self.ma_fixed = gtk.Fixed()
        self.button1 = gtk.Button("Start Model Adaption")
        self.button1.connect("clicked", self.start_ma)
        self.button1.set_tooltip_text("This button will close this window")
        self.button1.show()
        self.ma_fixed.put(self.button1, 1, 10)

        self.button2 = gtk.Button("Stop Model Adaption")
        self.button2.connect("clicked", self.stop_ma)
        self.button2.show()
        self.ma_fixed.put(self.button2, 156, 10)

        #Colored record button
        global ma_colorbutton
        ma_colorbutton = gtk.Button("RECORD")
        ma_colorbutton.connect("clicked", self.ma_is_clicked_button)
        #ma_colorbutton.show()
        self.ma_fixed.put(ma_colorbutton, 10, 250)

        #Infobox for the model-adaption tab
        self.sw_ma_info = gtk.ScrolledWindow()
        self.sw_ma_info.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.ma_info_textview = gtk.TextView()
        self.ma_info_textview.set_editable(False)
        self.ma_info_textview.set_wrap_mode(gtk.WRAP_WORD) #WRAP_WORD WRAP_CHAR
        global ma_info_textbuffer
        ma_info_textbuffer = self.ma_info_textview.get_buffer()
        ma_info_textbuffer.set_text('Click on "Start Model Adaption" to start! After that you are prompted to select the sentence file.')
        self.ma_info_textview.connect("size-allocate", self._autoscroll, self.sw_ma_info)
        self.ma_info_textview.set_size_request(-1, 100)
        self.ma_info_textview.show()
        self.sw_ma_info.add(self.ma_info_textview)
        self.sw_ma_info.show()

        self.ma_fixed.put(self.sw_ma_info, 1, 50)
        self.ma_info_textview.set_size_request(590, 150)

        self.ma_fixed.show()
        self.ma_hbox.pack_start(self.ma_fixed, False, False, 0)
        self.ma_hbox.show()


        #Textfield in the debug tab
        self.sw_output = gtk.ScrolledWindow()
        self.sw_output.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        textview_output = gtk.TextView()
        textview_output.set_editable(False)
        textview_output.set_wrap_mode(gtk.WRAP_WORD) #WRAP_WORD WRAP_CHAR
        textview_output.connect("size-allocate", self._autoscroll, self.sw_output)
        global textbuffer_output
        textbuffer_output = textview_output.get_buffer()
        self.sw_output.add(textview_output)
        textview_output.show()
        self.sw_output.show()
        
        #Create notebook with 3 tabs
        self.notebook = gtk.Notebook()
        self.notebook.set_scrollable(True)

        self.notebook.append_page(ps_vbox, gtk.Label('PocketSphinx Output'))
        self.notebook.append_page(self.ma_hbox, gtk.Label('Model Adaption'))
        self.notebook.append_page(self.sw_output, gtk.Label('Debug'))
        self.notebook.props.border_width = 1
        self.notebook.set_tab_reorderable(ps_vbox, True)
        self.notebook.set_tab_reorderable(self.ma_hbox, True)
        self.notebook.set_tab_reorderable(self.sw_output, True)
        self.notebook.show()
        vbox.pack_start(self.notebook)

        #create simple statusbar
        global statusbar
        statusbar = gtk.Statusbar()
        statusbar.set_has_resize_grip( False)
        statusbar.push(0, "Started succesfullly.")
        statusbar.show()
        vbox.pack_start(statusbar, expand=False)
        vbox.show()

        #self.window.add(fixed)
        window.add(vbox)
        window.show()
        window.connect("destroy", self.destroy)


    def main(self):
        #GObject.threads_init()
        gtk.gdk.threads_init()
        #gtk.gdk.threads_enter()
        gtk.main()
        #gtk.gdk.threads_leave()


if __name__ == '__main__':
    #Start the main GUI.
    base = Base()
    base.main()
