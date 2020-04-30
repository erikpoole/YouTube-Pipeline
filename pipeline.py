import os
import shutil
import time
from datetime import date

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

    mlt = MLTFile(date.today().strftime("%b-%d-%Y.mlt"))
    print(find_noisy_sections("audio_test_2.mp4"))
    mlt.write()

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

def find_noisy_sections(path):
    # not handling channels
    clip = VideoFileClip(path, audio_fps=AUDIO_FPS)
    print(clip.duration)
    print(clip.audio.fps)

    # chunk_duration is in seconds (e.g. "1" equals 44100), last chunk will have empty audio to pad the end
    # each sound value will have a range from 1 to -1, where 1 and -1 represent max volume
    audio_chunks = clip.audio.iter_chunks(chunk_duration=CHUNK_DURATION)
    noisy_sections = []
    noisy_start = -1
    noisy_end = -1
    num_sections = 0
    for index, chunk in enumerate(audio_chunks):
        num_sections = num_sections + 1
        if noisy_start < 0 and is_noisy(chunk):
            # if wasn't noisy and now is - set noisy_start
            noisy_start = index
            next
        if noisy_start >= 0 and not is_noisy(chunk):
            if noisy_end < 0:
                # if was noisy and now isn't - set noisy_end
                noisy_end = index
                next
            if index - noisy_end >= SILENT_CHUNKS_REQUIRED:
                # if hasn't been noisy for SILENT_CHUNKS_REQUIRED, add noisy section
                add_noisy_section(clip.duration, noisy_sections, noisy_start, noisy_end)
                noisy_start = -1
                noisy_end = -1

    # catch last section if noisy
    if noisy_start >= 0:
        add_noisy_section(clip.duration, noisy_sections, noisy_start, (num_sections - 1))
    
    return noisy_sections
    
def is_noisy(chunk):
    if (abs(np.amin(chunk)) > AUDIO_THRESHOLD):
        return True
    return False

def add_noisy_section(seconds_upper_bound, sections, start, end):
    # pads sounded sections with silence
    starting_chunk = start - SILENCE_PADDING_CHUNKS
    starting_second = chunk_index_to_seconds(starting_chunk)
    if starting_second < 0:
        starting_second = 0
    starting_timestamp = seconds_to_timestamp(starting_second)

    ending_chunk = end + SILENCE_PADDING_CHUNKS
    ending_second = chunk_index_to_seconds(ending_chunk)
    if ending_second > seconds_upper_bound:
        ending_second = seconds_upper_bound
    ending_timestamp = seconds_to_timestamp(ending_second)

    sections.append([starting_timestamp, ending_timestamp])

def chunk_index_to_seconds(index):
    return index * CHUNK_DURATION

def seconds_to_timestamp(seconds):
    partial_seconds = seconds - int(seconds)
    formatted_seconds = '{:.3f}'.format(partial_seconds).lstrip('0')
    return "%s%s" % (time.strftime("%H:%M:%S", time.gmtime(seconds)), formatted_seconds)

# needs rework to be add nodes for one video
# def add_video_nodes(tree, file_paths):
#     video_playlist = tree.find(".//*[@id='video_playlist']")
#     for index, path in enumerate(file_paths):
#         clip_length = VideoFileClip(path).duration

#         # add playlist entry
#         entry = et.Element('entry')
#         entry.attrib["producer"] = str(index)
#         entry.attrib["in"] = "00:00:00.000"
#         entry.attrib["out"] = seconds_to_timestamp(clip_length)
#         video_playlist.append(entry)
        
#         # add producer entry
#         producer = get_element_from_template("producer")
#         producer.attrib["id"] = str(index)
#         producer.attrib["out"] = "00:00:" + str(clip_length)
#         producer.find(".//*[@name='length']").text = "00:00:" + str(clip_length)
#         producer.find(".//*[@name='resource']").text = path
#         producer.find(".//*[@name='shotcut:caption']").text = path
#         producer.find(".//*[@name='shotcut:detail']").text = path
#         # producers must be inserted above playlists and tractor to satisfy shotcut
#         tree.insert(2 + index, producer)

class MLTFile:
    def __init__(self, name):
        self.name = name
        self.root = self.__get_element_from_template("skeleton")
        self.producer_number = 0

    def __get_element_from_template(self, name):
        path = "./xml_templates/" + name + ".xml"
        tree = et.parse(path, et.XMLParser(remove_blank_text=True))
        return tree.getroot()

    # def add_video_with_edits():


    def write(self):
        et.ElementTree(self.root).write(self.name, pretty_print=True)

def cleanup_last_run():
    if os.path.exists(CLIPS_DIR):
        shutil.rmtree(CLIPS_DIR)

    if os.path.exists("./TEMP"):
        shutil.rmtree("./TEMP")

main()