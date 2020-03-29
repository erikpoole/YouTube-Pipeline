import os
import shutil
import subprocess

CLIPS_DIR = "./clips"

def main():
    cleanup_last_run()

    print("moving files from pending")
    os.mkdir(CLIPS_DIR)
    file_paths = copy_pending_files()

    print("removing silence")
    remove_silence(file_paths)

def cleanup_last_run():
    if os.path.exists(CLIPS_DIR):
        shutil.rmtree(CLIPS_DIR)

    if os.path.exists("./TEMP"):
        shutil.rmtree("./TEMP")

def copy_pending_files():
    # consider passing as argument
    PENDING_PATH = "/mnt/c/Users/Mahkumazahn/Videos/Pending"

    original_names = os.listdir(PENDING_PATH)
    original_paths = [os.path.join(PENDING_PATH, original_name) for original_name in original_names]
    original_paths.sort(key=lambda original_path: os.path.getctime(original_path))

    new_paths = []
    for index, original_path in enumerate(original_paths):
        new_path = os.path.join(CLIPS_DIR, str(index) + ".mp4")

        # TODO: use shutil.move when pipeline is complete
        shutil.copy(original_path, new_path)
        new_paths.append(new_path)

    return new_paths

def remove_silence(file_paths):
    for path in file_paths:
        # both libraries dramatically lower size and bitrate... this is probably a problem
        # cannot open files in wsl from shotcut, have to move to pending first!!!

        # Increases audio volume
        # os.system("python3 ./jumpcutter/jumpcutter.py --input_file %s --output_file %s --sounded_speed 1 --silent_speed 999999 --frame_margin 10 --sample_rate 48000" % (path, path.replace(".mp4", "_result.mp4")))

        # Doesn't work with .flv files
        os.system("./video-remove-silence/video-remove-silence " + path)

        # os.remove(path)
        # os.rename(path.replace(".mp4", "_result.mp4"), path)
        break

main()