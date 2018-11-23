import os
import zipfile

def zip_file(path_to_files, uncompressed, zipped, zip_file):
    '''
    writes zip file to path_to_files + zipped consisting of all
    files and recursively all subdirectories and contents located
    at path_to_files + uncompressed 
    '''
    zf = zipfile.ZipFile(path_to_files + zipped + zip_file, "w")
    for dirname, subdirs, files in os.walk(path_to_files + uncompressed):
        for filename in files:
            path = os.path.join(dirname, filename)
            zf.write(os.path.join(dirname, filename), arcname=filename)
    zf.close()

