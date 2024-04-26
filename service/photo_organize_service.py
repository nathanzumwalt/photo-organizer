from piwigo import Piwigo
import logging
import threading
import os
import signal
import hashlib
import time 
import exifread
import pprint
import os
import hashlib
import glob
import sys
import shutil
import urllib.request
import json
#from dateutil.relativedelta import *
#from dateutil.easter import *
#from dateutil.rrule import *
from dateutil.parser import parse as duparse
from datetime import datetime

# Config ####################################

piwigo_server = 'http://localhost'
piwigo_username = 'nathanz'
piwigo_password = 'Jupe1234'

photos_process_dir = '/mnt/cathy-nas/Photos_To_Process/'
photos_root_dir = '/mnt/cathy-nas/Photos/'
photos_error_dir = '/mnt/cathy-nas/Photos_Process_Errored/'
photos_error_dir_dupe = os.path.join('/mnt/cathy-nas/Photos_Process_Errored/', 'Duplicate')

photos_backup_dir = "/mnt/nathan-nas/Backups/Pixel 6a 2024/"

dry_run = False

piwigosite = Piwigo(piwigo_server)
piwigosite.pwg.session.login(username=piwigo_username, password=piwigo_password)
pwg_token = piwigosite.pwg.session.getStatus()['pwg_token']

run = True 

backup_photo_cache = {}
backup_photo_cache_path = '/tmp/backup_photo_cache_path.json'
if os.path.exists(backup_photo_cache_path):
	f = open(backup_photo_cache_path)
	backup_photo_cache = json.load(f)

# Logging
def log(message, photo_file_name=None, show_timestamp=False):
	
	dt = datetime.now()
	#ts = datetime.timestamp(dt)
	
	if photo_file_name != None:
		if show_timestamp:
			print("[{}] {}".format(photo_file_name, message), dt)
		else:
			print("[{}] {}".format(photo_file_name, message))
			
	else:
		if show_timestamp:
			print(message, dt)

		else:
			print(message)


# Handle stop signal from systemd
def handler_stop_signals(signum, frame):
	log("in stop_signals: " + str(signum) + " " + str(frame))
	global run
	run = False
	log("waiting for threads to complete")


# Update md5sum on all photos in piwigo
def piwigo_photo_set_md5sums():
	response = piwigosite.pwg.images.setMd5sum(block_size="20", pwg_token=pwg_token)
	log(response)

	while response['nb_no_md5sum'] > 0 :
       		response = piwigosite.pwg.images.setMd5sum(block_size="20", pwg_token=pwg_token)
        	log(response)

def get_photo_date_taken(photo_file_name):
	""" Extract the date the photo was taken using the embedded EXIF data
	    or filename as a string in yyyy-mm-dd format
	"""

	# Read the EXIF data
	f = open(photo_file_name, 'rb')
	tags = exifread.process_file(f)

	if 'EXIF DateTimeOriginal' in tags:
		return tags['EXIF DateTimeOriginal'].values[:10].replace(':', '-')
	elif 'EXIF DateTimeDigitized' in tags:
		return tags['EXIF DateTimeDigitized'].values[:10].replace(':', '-')
	else:
		log("Can't determine when the photo was taken from EXIF data", photo_file_name)

		#try getting a date from the filename 
		try:
			result = duparse(os.path.basename(photo_file_name), fuzzy_with_tokens=True)
			if isinstance(result[0], datetime):
				return result[0].strftime("%Y-%m-%d")
		except Exception as e:
			#Catch and swallow any exceptions that come from the parse (assume parse failure)
			x = None
			
		return None

def piwigo_photo_exists(photo_file_name):
	#Check for photo in piwigo
	photo_hash = hashlib.md5(open(photo_file_name, 'rb').read()).hexdigest()
	log("photo_hash=" + photo_hash, photo_file_name)

	photo_exists = piwigosite.pwg.images.exist(md5sum_list=photo_hash)
	log("photo_exists(1)=" + str(photo_exists), photo_file_name)

	#The photo seems to exist, recalculate the md5sum to be sure (have had issues where md5sums are "wrong")
	if photo_exists[photo_hash] != None:
		#Photo exists, delete the md5sum
		with urllib.request.urlopen("http://photos.zumwalthome.com/ws.php?format=json&method=zumwalt_home.resetMd5sum&md5sum=" + photo_hash) as url:
			response = json.load(url)

		#Recalculate the md5sum
		piwigo_photo_set_md5sums()
		
		#Check the photo_hash again
		photo_exists = piwigosite.pwg.images.exist(md5sum_list=photo_hash)
		log("photo_exists(2)=" + str(photo_exists), photo_file_name)

	return photo_exists[photo_hash] != None

def process_backup_dirs():

	for filename in glob.iglob(photos_backup_dir + "/**/*.jpg", recursive=True):

		log_message = ""
		photo_hash = hashlib.md5(open(filename, 'rb').read()).hexdigest()
		if photo_hash not in backup_photo_cache.keys(): 
			if not piwigo_photo_exists(filename):
				#Copy the photo to the process dir so that it can be picked up and processed
				path = os.path.join(photos_process_dir, os.path.basename(filename))
				#log_message += "copy from to " + path
				if not dry_run:
					shutil.copy(filename, path)
			else:
				log_message += "duplicate"

			#Add the hash to the cache
			backup_photo_cache[photo_hash] = filename
			with open(backup_photo_cache_path, 'w', encoding='utf-8') as f:
    				json.dump(backup_photo_cache, f)
		else:
			log_message += "cache hit!"

		log(log_message, filename)
			
	


def process_photos(photo_directory, photo_root_dir, photo_error_dir, dry_run):
	""" Move all the photos in the given directory, based on move_photo.  If
	    dry_run is set, the file won't actually be moved.
	"""
	for filename in glob.iglob(photo_directory + "/**/*.*", recursive=True):
		process_photo(filename, photo_root_dir, photo_error_dir, dry_run)

def get_photo_path(photo_file_name, photo_root_dir, dedupe=False):
	date_taken = get_photo_date_taken(photo_file_name)

	path = os.path.join(photo_root_dir, date_taken[0:4], date_taken)
	path = os.path.join(path, os.path.basename(photo_file_name))


	if os.path.exists(path) and  dedupe :
		log_string = "Photo filename already exists."

		x = 0
		filename_exists = True
		while (filename_exists):
			x = x + 1
			filename = os.path.splitext(path)[0] + '_' + str(x) + os.path.splitext(path)[1]
			path = os.path.join(os.path.dirname(path), filename)

			filename_exists = os.path.exists(path)

	return path

def dedupe_file(path):
	if os.path.exists(path):
		log_string = "Filename already exists."

		x = 0
		filename_exists = True
		while (filename_exists):
			x = x + 1
			filename = os.path.splitext(path)[0] + '_' + str(x) + os.path.splitext(path)[1]
			path = os.path.join(os.path.dirname(path), filename)

			filename_exists = os.path.exists(path)

	return path
	

def photo_exists(photo_file_name, photo_root_dir):
	""" Detects if a file with the same name already exists in the path AND has the same hash.
            (Assumes detection of a photo with the same hash is detected via piwigo APIs)
	"""

	path = get_photo_path(photo_file_name, photo_root_dir, False)

	if os.path.exists(path):
		return hashlib.md5(open(path, 'rb').read()).hexdigest() == hashlib.md5(open(photo_file_name, 'rb').read()).hexdigest()
	
	else:
		return False

def process_photo(photo_file_name, photo_root_dir, photo_error_dir, dry_run):
	""" Move the photo to the root, based on get_photo_path.  If
            dry_run is set, the file won't actually be moved.
	"""

	if os.path.basename(photo_file_name) == 'Thumbs.db':
		return

	log_message = ""
	
	if piwigo_photo_exists(photo_file_name):
		process_error_photo(photo_file_name, 'duplicate')
		log_message += " duplicate"
		log(log_message, photo_file_name)
		return

	date_taken = get_photo_date_taken(photo_file_name)
	if date_taken is None:
		process_error_photo(photo_file_name, 'no_date')
		log_message += " no_date_taken"
		log(log_message, photo_file_name)
		return

	if photo_exists(photo_file_name, photo_root_dir):
		process_error_photo(photo_file_name, 'duplicate')
		log_message += " duplicate"
		log(log_message, photo_file_name)
		return

	# Get the new path, deduped if necessary
	new_photo_path = get_photo_path(photo_file_name, photo_root_dir, True)

	log_message += " new_path:" + new_photo_path
	log(log_message, photo_file_name)

	# Perform the actual move
	if not dry_run:
		if not os.path.isdir(os.path.dirname(new_photo_path)):
			os.makedirs(os.path.dirname(new_photo_path))
		shutil.move(photo_file_name, new_photo_path)
		

def process_error_photo(photo_file_name, error_type):
	if error_type == 'duplicate':
		#log("Process errored photo: duplicate", photo_file_name)
		path = dedupe_file(os.path.join(photos_error_dir_dupe, os.path.basename(photo_file_name)))
		#log("new path:" + path)
		shutil.move(photo_file_name, path)
	#elif error_type == 'no_date':
		#log("Process errored photo: no_date", photo_file_name)
	#else:
	#	log("Process errored photo: unspecified", photo_file_name)
	

def piwigo_sync_photos():
	#sudo perl remote_sync.pl --base_url=http://localhost --username=nathanz --password=Jupe1234
	#/var/www/html/tools
	os.system('cd /var/www/html/tools; perl remote_sync.pl --base_url=http://localhost --username=nathanz --password=Jupe1234 > /dev/null')

def piwigo_get_tag_id(tag_name):

	tag_list = piwigosite.pwg.tags.getAdminList()

	for tag in tag_list['tags']: 
		#log(tag)
		if tag['name'] == tag_name:
			return tag['id'] 

	#Tag doesn't exist, so create it
	response = piwigosite.pwg.tags.add(name=tag_name)
	#log(response)

	return response['id']

def photo_tagged(photo_info, tag_name):
	for tag in photo_info['tags']:
		if tag['name'] == tag_name:
			return True

	return False


def piwigo_tag_photo_locations(photo_id):

	log_message = "Tagging locations; processing image " + str(photo_id)

	photo_info = piwigosite.pwg.images.getInfo(image_id=photo_id)
	if photo_tagged(photo_info, 'geotagged'):
		log_message += " already geotagged"
		#log(log_message)
		return
	
	try:

		# Sync meta data before geotagging (may be needed if the lat/lon hasn't been synced from the exif data
		piwigosite.pwg.images.syncMetadata(image_id=photo_id, pwg_token=pwg_token)
		# Now that the meta data has been synced, refresh the photo info
		photo_info = piwigosite.pwg.images.getInfo(image_id=photo_id)
	except Exception as ex:

		log(log_message)

		error_message = str(ex)
		print(error_message)
		print(type(error_message))
	

	if 'latitude' in photo_info and photo_info['latitude'] != None and photo_info['latitude'] != '0.000000' and 'longitude' in photo_info and photo_info['longitude'] != None and photo_info['longitude'] != '0.000000':

		log_message += " found lat/long" 
		nominatim_url = "https://nominatim.openstreetmap.org/reverse?lat=" + photo_info['latitude'] + "&lon=" + photo_info['longitude'] + "&format=json"

		log_message += nominatim_url


		with urllib.request.urlopen(nominatim_url) as url:
			data = json.load(url)
			log_message += str(data['address'])

		#Throttle calls to nominatim
		time.sleep(1)

		if 'address' in data:

			#Include any of these attributes as tags in the photo
			attribute_names = ['man_made', 'place', 'building', 'hamlet', 'retail', 'village', 'town', 'city', 'state', 'tourism', 'shop', 'leisure', 'amenity', 'office', 'historic', 'industrial']

				
			#If country isn't the US, add that too
			if 'country' in data['address']:
				if data['address']['country'] != 'United States':	
					attribute_names.extend(['country', 'road', 'city_block', 'suburb', 'city_district', 'county'])

			#If if a city wasn't given, use the county
			if 'village' not in data['address'] and 'town' not in data['address'] and 'city' not in data['address'] and 'hamlet' not in data['address']:
				if 'county' in data['address']:
					attribute_names.extend(['county'])

			#Add all the attributes
			for attribute_name in attribute_names:
				if attribute_name in data['address']:
					piwigosite.pwg.images.setInfo(image_id=photo_id, tag_ids=piwigo_get_tag_id(data['address'][attribute_name]))
			
	else:
		log_message += " no lat/long"

	#Mark photo as geotagged
	piwigosite.pwg.images.setInfo(image_id=photo_id, tag_ids=piwigo_get_tag_id('geotagged'))

	log(log_message)

def piwigo_tag_all_photo_locations():

	with urllib.request.urlopen("http://photos.zumwalthome.com/ws.php?format=json&method=zumwalt_home.getImagesToGeotag") as url:

		response = json.load(url)

		for image_id in response['result']['images']:
			piwigo_tag_photo_locations(image_id)

# Main service loop
while run:

	#Sync photos in piwigo
	log("Initial Sync photos ---------------------------------------------------------", show_timestamp=True)
	piwigo_sync_photos()

	#Update hashes on the server (in case some have been added since the last run)
	log("Setting md5sums -------------------------------------------------------------", show_timestamp=True)
	piwigo_photo_set_md5sums()

	log("Processing backup dirs  -----------------------------------------------------", show_timestamp=True)
	process_backup_dirs()

	#Move and organize photos
	log("Processing photos -----------------------------------------------------------", show_timestamp=True)
	process_photos(photos_process_dir, photos_root_dir, photos_error_dir, dry_run)

	#Sync photos in piwigo
	log("Syncing photos again --------------------------------------------------------", show_timestamp=True)
	piwigo_sync_photos()

	#Update hashes on the server (in case some have been added since the last run)
	log("Setting md5sums -------------------------------------------------------------", show_timestamp=True)
	piwigo_photo_set_md5sums()

	#Add tags for locations based on reverse geocoding
	log("Tagging photos with locations -----------------------------------------------", show_timestamp=True)
	piwigo_tag_all_photo_locations()

	log("Sleeping --------------------------------------------------------------------", show_timestamp=True)
	#time.sleep(1 * 60 * 60)
	#time.sleep(10)

	#Only run once
	run = False
