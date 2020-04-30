import os
import shutil
import time

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

# moving files maybe not necessary if we're not actually editing files, just creating xml
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

def find_silences(path):
    # not handling channels
    clip = VideoFileClip(path, audio_fps=AUDIO_FPS)
    print(clip.duration)
    print(clip.audio.fps)

    # chunk_duration is in seconds (e.g. "1" equals 44100), last chunk will have empty audio to pad the end
    # each sound value will have a range from 1 to -1, where 1 and -1 represent max volume
    audio_chunks = clip.audio.iter_chunks(chunk_duration=CHUNK_DURATION)
    silent_sections = []
    section_start = -1
    num_sections = 0
    for index, chunk in enumerate(audio_chunks):
        num_sections = num_sections + 1
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
    if section_start >= 0 and (num_sections - 1) - section_start >= SILENT_CHUNKS_REQUIRED:
        add_silent_section(silent_sections, section_start, (num_sections - 1))
    
    return silent_sections
    
def is_silent(chunk):
    if (abs(np.amin(chunk)) > AUDIO_THRESHOLD) or np.amax(chunk) > AUDIO_THRESHOLD:
        return False
    return True

def add_silent_section(sections, start, end):
    # pads sounded sections with silence
    starting_chunk = start + SILENCE_PADDING_CHUNKS
    ending_chunk = end - SILENCE_PADDING_CHUNKS

    starting_second = chunk_index_to_seconds(starting_chunk)
    ending_second = chunk_index_to_seconds(ending_chunk)
    starting_timestamp = seconds_to_timestamp(starting_second)
    ending_timestamp = seconds_to_timestamp(ending_second)

    sections.append([starting_timestamp, ending_timestamp])

def chunk_index_to_seconds(index):
    return index * CHUNK_DURATION

def seconds_to_timestamp(seconds):
    partial_seconds = seconds - int(seconds)
    return "%s%.3f" % (time.strftime("%H:%M:%S", time.gmtime(seconds)), partial_seconds)
    
def get_element_from_template(name):
    path = "./xml_templates/" + name + ".xml"
    tree = et.parse(path, et.XMLParser(remove_blank_text=True))
    return tree.getroot()

# needs rework to be add nodes for one video
def add_video_nodes(tree, file_paths):
    video_playlist = tree.find(".//*[@id='video_playlist']")
    for index, path in enumerate(file_paths):
        clip_length = VideoFileClip(path).duration

        # add playlist entry
        entry = et.Element('entry')
        entry.attrib["producer"] = str(index)
        entry.attrib["in"] = "00:00:00.000"
        entry.attrib["out"] = seconds_to_timestamp(clip_length)
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

main()