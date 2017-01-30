<?php
function dirToArray($dir) { 
   
   $result = array(); 

   $cdir = scandir($dir); 
   foreach ($cdir as $key => $value) 
   { 
      if (!in_array($value,array(".",".."))) 
      { 
         if (is_dir($dir . DIRECTORY_SEPARATOR . $value)) 
         { 
            $result[$value] = dirToArray($dir . DIRECTORY_SEPARATOR . $value); 
         } 
         else 
         { 
            //$result[] = $dir . DIRECTORY_SEPARATOR . $value . "\t" . hash_file('crc32', $dir . DIRECTORY_SEPARATOR . $value); 
			echo $dir . DIRECTORY_SEPARATOR . $value . "\t" . hash_file('crc32', $dir . DIRECTORY_SEPARATOR . $value) . "\n"; 
         } 
      } 
   } 
   
   return $result; 
} 


$rootFolder = 'C:\Users\zumwaltn\Documents\DCIM';

$directoryList = dirToArray($rootFolder);
//$hash = hash_file('crc32', 'C:\Users\zumwaltn\Documents\steam-sale-flight-simulator-130-off.png');

//print_r($directoryList);