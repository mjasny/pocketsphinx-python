pocketsphinx-python
===================

A GTK Python GUI for pocketsphinx. Continuous recognition and automatic model-adaption are available.


I recommend building the latest sphinxbase, pocketsphinx and sphinxtrain from source.

https://github.com/cmusphinx/sphinxbase
https://github.com/cmusphinx/pocketsphinx
https://github.com/cmusphinx/sphinxtrain

To run the application do:

./voice.py

If you get a decoder error, caused by wrong locales do this:
LANG=''; LC_ALL=''; ./main.py
