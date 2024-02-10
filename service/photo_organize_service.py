from piwigo import Piwigo
import logging
import threading
import os
import signal
import hashlib
import time

mysite = Piwigo('http://localhost')
mysite.pwg.session.login(username="nathanz", password="Jupe1234")
pwg_token = mysite.pwg.session.getStatus()['pwg_token']


#########################################################################
# Handle stop signal from systemd
def handler_stop_signals(signum, frame):
	print("in stop_signals: " + str(signum) + " " + str(frame))
	global run
	run = False
	print("waiting for threads to complete")

#########################################################################

run = True

while run:
	
	response = mysite.pwg.images.setMd5sum(block_size="20", pwg_token=pwg_token)
	print(response)

	while response['nb_no_md5sum'] > 0 :
       		response = mysite.pwg.images.setMd5sum(block_size="20", pwg_token=pwg_token)
        	print(response)

	time.sleep(10)
