import os
import shutil
import subprocess

TEMP_DIR = "./clips"

def main():
    cleanup_last_run()

    print("moving files from pending")
    os.mkdir(TEMP_DIR)
    file_paths = copy_pending_files()

    print("removing silence")
    remove_silence(file_paths)

def cleanup_last_run():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

def copy_pending_files():
    # consider passing as argument
    PENDING_PATH = "/mnt/c/Users/Mahkumazahn/Videos/Pending"

    original_names = os.listdir(PENDING_PATH)
    original_paths = [os.path.join(PENDING_PATH, original_name) for original_name in original_names]
    original_paths.sort(key=lambda original_path: os.path.getctime(original_path))

    print(original_paths)

    new_paths = []
    for index, original_path in enumerate(original_paths):
        new_path = os.path.join(TEMP_DIR, str(index) + ".mp4")

        # TODO: use shutil.move when pipeline is complete
        shutil.copy(original_path, new_path)
        new_paths.append(new_path)

    return new_paths

def remove_silence(file_paths):
    for path in file_paths:
        os.system("./video-remove-silence/video-remove-silence " + path)
        os.remove(path)
        os.rename(path.replace(".mp4", "_result.mp4"), path)
        break

main()