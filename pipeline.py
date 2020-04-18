import os
import shutil
import lxml.etree as et

from moviepy.editor import VideoFileClip

CLIPS_DIR = "./clips"

def main():
    cleanup_last_run()

    # moving files maybe not necessary if we're not actually removing space, 
    # just creating xml
    print("moving files from pending")
    os.mkdir(CLIPS_DIR)
    file_paths = copy_pending_files()

    root = get_element_from_template("skeleton")
    add_video_nodes(root, file_paths)

    # print("removing silence")
    # remove_silence(file_paths)

    # will need a rename
    et.ElementTree(root).write("output.mlt", pretty_print=True)

def get_element_from_template(name):
    path = "./xml_templates/" + name + ".xml"
    tree = et.parse(path, et.XMLParser(remove_blank_text=True))
    return tree.getroot()

def add_video_nodes(tree, file_paths):
    video_playlist = tree.find(".//*[@id='video_playlist']")
    for index, path in enumerate(file_paths):
        clip_length = VideoFileClip(path).duration

        # add playlist entry
        entry = et.Element('entry')
        entry.attrib["producer"] = str(index)
        entry.attrib["in"] = "00:00:00.000"
        # TODO Will need it's own method, not sure how this handles minutes
        entry.attrib["out"] = "00:00:" + str(clip_length)
        video_playlist.append(entry)
        
        # add producer entry
        producer = get_element_from_template("producer")
        producer.attrib["id"] = str(index)
        producer.attrib["out"] = "00:00:" + str(clip_length)
        producer.find(".//*[@name='length']").text = "00:00:" + str(clip_length)
        producer.find(".//*[@name='resource']").text = path
        producer.find(".//*[@name='shotcut:caption']").text = path
        producer.find(".//*[@name='shotcut:detail']").text = path
        # producers must be inserted above playlists and tractor to satisfy shotcut
        tree.insert(2 + index, producer)

def cleanup_last_run():
    if os.path.exists(CLIPS_DIR):
        shutil.rmtree(CLIPS_DIR)

    if os.path.exists("./TEMP"):
        shutil.rmtree("./TEMP")

def copy_pending_files():
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
        # shotcut videos are blank when the reference is inside wsl

        # Increases audio volume
        # os.system("python3 ./jumpcutter/jumpcutter.py --input_file %s --output_file %s --sounded_speed 1 --silent_speed 999999 --frame_margin 10 --sample_rate 48000" % (path, path.replace(".mp4", "_result.mp4")))

        # Doesn't work with .flv files
        os.system("./video-remove-silence/video-remove-silence " + path)

        # os.remove(path)
        # os.rename(path.replace(".mp4", "_result.mp4"), path)
        break

main()