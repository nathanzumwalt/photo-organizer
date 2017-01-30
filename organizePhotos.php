<?php

error_reporting(E_ERROR | E_PARSE);

function movePhoto($photoFileName, $photoRootDir) {
	
	$exif = exif_read_data($photoFileName, 'IFD0', true, false);
	
	if ( $exif != false ) {
		
		if ( array_key_exists('DateTime', $exif['IFD0']) ) {
		
			//Get the date the picture was taken
			$dateTime = date('Y-m-d', strtotime($exif['IFD0']["DateTime"]));
			
			//If the date directory doesn't exist, create it
			if ( !file_exists($photoRootDir . DIRECTORY_SEPARATOR  . $dateTime) ) {
				mkdir($photoRootDir . DIRECTORY_SEPARATOR  . $dateTime);
			} 
			
			$moveToFilePath = $photoRootDir . DIRECTORY_SEPARATOR  . $dateTime . DIRECTORY_SEPARATOR . basename($photoFileName);
			//Check to see if the file already exists
			if ( file_exists($moveToFilePath) ) {
				echo "File $moveToFilePath already exists\n";
				
				//Is it the same picture?
				if ( hash_file('crc32', $photoFileName) == hash_file('crc32', $moveToFilePath) ) {
					echo "$photoFileName and $moveToFilePath are duplicates.\n";
					
					$x = 1;
					$path_parts = pathinfo($moveToFilePath);
					do {
						$moveToFilePath = $path_parts['dirname'] . DIRECTORY_SEPARATOR .  $path_parts['filename'].'_DUP_'. $x . '.' . $path_parts['extension'];
						$x++;
					} while (file_exists($moveToFilePath));

					echo "Moving $photoFileName to ". $moveToFilePath . "\n";
					rename($photoFileName, $moveToFilePath);
					
				} else {
					echo "$photoFileName and $moveToFilePath are NOT duplicates.\n";
					
					$x = 1;
					$path_parts = pathinfo($moveToFilePath);
					do {
						$moveToFilePath = $path_parts['dirname'] . DIRECTORY_SEPARATOR .  $path_parts['filename'] . '_' . $x . '.' . $path_parts['extension'];
						$x++;
					} while (file_exists($moveToFilePath));

					echo "Moving $photoFileName to ". $moveToFilePath . "\n";
					rename($photoFileName, $moveToFilePath);
				}
				
			} else {
				//Move the file into the date directory
				logMessage("Moving to ". $moveToFilePath, $photoFileName);
				rename($photoFileName, $moveToFilePath);
			}
			
		
		} else {
			logMessage("Date not found in exif data", $photoFileName);	
		}
		
	} else {
		logMessage("No exif data found", $photoFileName);	
	}	
}

function logMessage($message, $photoFileName = null) {
	if ( $photoFileName != null )
		echo "[$photoFileName] $message \n";
	else 
		echo "$message\n";
}

function Get_ImagesToFolder($dir){
    $ImagesArray = [];
    $file_display = [ 'jpg', 'jpeg', 'png', 'gif' ];

    if (file_exists($dir) == false) {
        return ["Directory \'', $dir, '\' not found!"];
    } 
    else {
        $dir_contents = scandir($dir);
        foreach ($dir_contents as $file) {
            $file_type = strtolower(pathinfo($file, PATHINFO_EXTENSION));
            if (in_array($file_type, $file_display) == true) {
                $ImagesArray[] = $dir . DIRECTORY_SEPARATOR . $file;
            }
        }
        return $ImagesArray;
    }
}
	
function organizeDirectory($dirToProcess, $photoRootDir)  {
	$imagesToProcess = Get_ImagesToFolder($dirToProcess);
	
	foreach ($imagesToProcess as $imageToProcess) {
		movePhoto($imageToProcess, $photoRootDir);
	}
}

function organizeDirectories($dirToProcess, $photoRootDir)  {
	$iter = new RecursiveIteratorIterator(
		new RecursiveDirectoryIterator($dirToProcess, RecursiveDirectoryIterator::SKIP_DOTS),
		RecursiveIteratorIterator::SELF_FIRST,
		RecursiveIteratorIterator::CATCH_GET_CHILD // Ignore "Permission denied"
	);

	$paths = array($dirToProcess);
	foreach ($iter as $path => $dir) {
		if ($dir->isDir()) {
			$paths[] = $path;
		}
	}

	//print_r($paths);
	foreach ($paths as $path) {
		organizeDirectory($path, $photoRootDir);
	}
	
	
	
}
	
//movePhoto('C:\Users\zumwaltn\Documents\DCIM\\898GXDFM\IMG_1560.PNG', 'C:\Users\zumwaltn\Documents\Photos');
//organizeDirectory('C:\Users\zumwaltn\Documents\DCIM\834LVJAU', 'C:\Users\zumwaltn\Documents\Photos');
organizeDirectories('C:\Users\zumwaltn\Documents\DCIM', 'C:\Users\zumwaltn\Documents\Photos');