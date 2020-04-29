import os
import shutil

from moviepy.editor import VideoFileClip
import numpy as np
import lxml.etree as et

CLIPS_DIR = "./clips"
VIDEO_FPS = 30
AUDIO_FPS = 48000
CHUNK_DURATION = .1             # in seconds
SILENT_CHUNKS_REQUIRED = 10
SILENCE_PADDING_CHUNKS = 2
AUDIO_THRESHOLD = .03           # stolen from jumpcutter, might need tweaking

def main():
    # cleanup_last_run()

    # moving files maybe not necessary if we're not actually removing space, 
    # just creating xml
    # print("moving files from pending")
    # os.mkdir(CLIPS_DIR)
    # file_paths = copy_pending_files()

    # root = get_element_from_template("skeleton")
    # add_video_nodes(root, file_paths)

    # print("removing silence")
    # remove_silence(file_paths)

    # will need a rename
    # et.ElementTree(root).write("output.mlt", pretty_print=True)

    print(find_silences("audio_test.mp4"))

def find_silences(path):
    # not handling channels
    # verify audio fps is 44.1khz as opposed to 48khz, if not pass argument "audio_fps=48000"
    clip = VideoFileClip(path, audio_fps=AUDIO_FPS)
    print(clip.duration)
    print(clip.audio.fps)

    # chunk_duration is in seconds (e.g. "1" equals 44100), last chunk will have empty audio to pad the end
    # each sound value will have a range from 1 to -1, where 1 and -1 represent max volume
    audio_chunks = clip.audio.iter_chunks(chunk_duration=CHUNK_DURATION)
    silent_sections = []
    section_start = -1
    for index, chunk in enumerate(audio_chunks):
        if section_start < 0 and is_silent(chunk):
            # start silent_section
            section_start = index
            next
        if section_start >= 0 and not is_silent(chunk):
            # end silent_section
            if index - section_start >= SILENT_CHUNKS_REQUIRED:
                # start is inclusive, end is exclusive
                add_silent_section(silent_sections, section_start, index)
            section_start = -1
            next
    
    # catch last section if empty
    if section_start >= 0 and (len(tuple(audio_chunks)) - 1) - section_start >= SILENT_CHUNKS_REQUIRED:
        add_silent_section(silent_sections, section_start, len(tuple(audio_chunks) - 1))
    
    return silent_sections
    
def is_silent(chunk):
    if (abs(np.amin(chunk)) > AUDIO_THRESHOLD) or np.amax(chunk) > AUDIO_THRESHOLD:
        return False
    return True

def add_silent_section(sections, start, end):
    # Pads sounded sections with silence
    sections.append([start + SILENCE_PADDING_CHUNKS, end - SILENCE_PADDING_CHUNKS])

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