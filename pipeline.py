import os
import shutil
import subprocess

PENDING_PATH = "/mnt/c/Users/Mahkumazahn/Videos/Pending"
TEMP_DIR = "./clips"

# TODO: Make paths less nightmarish

print("moving files from pending")
os.mkdir(TEMP_DIR)

filenames = os.listdir(PENDING_PATH)
filepaths = [os.path.join(PENDING_PATH, filename) for filename in filenames]
filepaths.sort(key=lambda filepath: os.path.getctime(filepath))

for index, filepath in enumerate(filepaths):
    # TODO: use shutil.move when pipeline is complete
    shutil.copy(filepath, os.path.join(TEMP_DIR, str(index) + ".mp4"))

print("removing silence")
clip_names = os.listdir(TEMP_DIR)
for clip_name in clip_names:
    os.system("./video-remove-silence/video-remove-silence " + os.path.join(TEMP_DIR, clip_name))

shutil.rmtree(TEMP_DIR)

