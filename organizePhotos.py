import exifread 
import pprint
import os
import hashlib
import glob
import sys

def log(message, photo_file_name=None):
	if photo_file_name != None:
		print("[{}] {}".format(photo_file_name, message))
		
	else:
		print(message)
	

def get_photo_date_taken(photo_file_name):
	""" Extract the date the photo was taken using the embedded EXIF data
	"""
	
	# Read the EXIF data
	f = open(photo_file_name, 'rb')
	tags = exifread.process_file(f)
	
	if 'EXIF DateTimeOriginal' in tags:
		return tags['EXIF DateTimeOriginal'].values[:10].replace(':', '-')
	elif 'EXIF DateTimeDigitized' in tags:
		return tags['EXIF DateTimeDigitized'].values[:10].replace(':', '-')

	raise Exception("Can't determine when the photo was taken, EXIF data not found: " + photo_file_name)

	
def get_photo_path(photo_file_name, photo_root_dir):
	""" Based on the date the photo was taken, determine the directory it 
	    belongs in, given the photo_root_dir.  If there is a collision, 
		change the filename based on it being a duplicate or not
	"""
	
	date_taken = get_photo_date_taken(photo_file_name)
	
	path = os.path.join(photo_root_dir, date_taken);
	path = os.path.join(path, os.path.basename(photo_file_name))
	
	is_dupe = False
	if os.path.exists(path):
		log_string = "Photo filename already exists."
		dupe = "";
		if hashlib.md5(open(path, 'rb').read()).hexdigest() == hashlib.md5(open(photo_file_name, 'rb').read()).hexdigest():
			log_string = "Photo filename already exists (duplicate detected)."
			dupe = "DUP_"
			is_dupe = True
		
		log(log_string, photo_file_name)
		
		x = 0
		filename_exists = True
		original_path = path
		while (filename_exists):
			path = original_path
			x = x + 1
			filename = os.path.splitext(path)[0] + '_' + dupe + str(x) + os.path.splitext(path)[1]
			path = os.path.join(os.path.dirname(path), filename)
			
			filename_exists = os.path.exists(path)
		
	return {"path":path, "is_dupe":is_dupe}
	
	
def move_photo(photo_file_name, photo_root_dir, dry_run, move_dupes=False):
	""" Move the photo to the root, based on get_photo_path.  If
	    dry_run is set, the file won't actually be moved.
	"""
	response = get_photo_path(photo_file_name, photo_root_dir)
	new_photo_path = response['path']
	is_dupe = response['is_dupe']
	
	if not is_dupe or (is_dupe and move_dupes):
	
		log("Moving " + photo_file_name + " to " + new_photo_path, photo_file_name)
		if not dry_run:
			if not os.path.isdir(os.path.dirname(new_photo_path)):
				os.makedirs(os.path.dirname(new_photo_path))
			os.rename(photo_file_name, new_photo_path)
	else:
		log("Duplicate detected; not moving", photo_file_name)

def organize_directory(photo_directory, photo_root_dir, dry_run, move_dupes=False):
	""" Move all the photos in the given directory, based on move_photo.  If
	    dry_run is set, the file won't actually be moved.
	"""
	for filename in glob.iglob(photo_directory + "/**/*.*", recursive=True):

		try: 
			move_photo(filename, photo_root_dir, dry_run, move_dupes)
		except Exception as error:
			log("Move photo failed: {0}".format(error), filename)

			
if len(sys.argv) < 3:
	raise Exception("The directory to process and the photo root is required.")

# Get options
dry_run = "--dry-run" in sys.argv
move_dupes = "--move-dupes" in sys.argv

if not os.path.isdir(sys.argv[1]):
	raise Exception("Directory not found: " + sys.argv[1])
	
if not os.path.isdir(sys.argv[2]):
	raise Exception("Directory not found: " + sys.argv[2])

organize_directory(sys.argv[1], sys.argv[2], dry_run, move_dupes)




