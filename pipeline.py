import os
import shutil
import time
from datetime import date

from moviepy.editor import VideoFileClip
import numpy as np
import lxml.etree as et

VIDEOS_PATH = "/mnt/c/Users/Mahkumazahn/Videos"
PENDING_PATH = VIDEOS_PATH + "/Pending"
VIDEO_FPS = 30
AUDIO_FPS = 48000
CHUNK_DURATION = .1             # in seconds
SILENT_CHUNKS_REQUIRED = 10
# TODO SILENCE_PADDING_CHUNKS is somewhat misleading, since value will be added on both sides of silence (also mismatched for start and end of video...)
SILENCE_PADDING_CHUNKS = 3
AUDIO_THRESHOLD = .03           # stolen from jumpcutter, might need tweaking

def main():
    print("sorting and moving files")
    output_path = "%s/%s" % (VIDEOS_PATH, date.today().strftime("%b-%d-%Y"))

    if not os.path.exists(output_path):
        os.mkdir(output_path)

    file_paths = move_files(PENDING_PATH, output_path)

    print("creating basic mlt file")
    mlt_file = MLTFile()

    for path in file_paths:
        print("reading %s for noisy sections" % get_filename(path))
        noisy_sections = find_noisy_sections(path)

        print("adding %s noisy sections to mlt file" % get_filename(path))
        producer_number = mlt_file.add_producer(path)
        for section in noisy_sections:
            mlt_file.add_playlist_entry(producer_number, section[0], section[1])
    
    mlt_file.write(os.path.join(output_path, date.today().strftime("%b-%d-%Y.mlt")))

def move_files(original_directory, new_directory):
    original_names = os.listdir(original_directory)
    original_paths = [os.path.join(original_directory, original_name) for original_name in original_names]
    original_paths.sort(key=lambda original_path: os.path.getctime(original_path))

    new_paths = []
    for index, original_path in enumerate(original_paths):
        new_path = os.path.join(new_directory, str(index) + ".mp4")
        shutil.move(original_path, new_path)
        new_paths.append(new_path)

    return new_paths

def find_noisy_sections(path):
    # not handling channels
    clip = VideoFileClip(path, audio_fps=AUDIO_FPS)

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

def get_filename(path):
    return path.split("/")[-1]

class MLTFile:
    def __init__(self):
        self.root = self.__get_element_from_template("skeleton")
        self.producer_count = 0

    def __get_element_from_template(self, name):
        path = "./xml_templates/" + name + ".xml"
        tree = et.parse(path, et.XMLParser(remove_blank_text=True))
        return tree.getroot()

    def add_producer(self, path):
        clip = VideoFileClip(path, audio_fps=AUDIO_FPS)
        index = self.producer_count
        filename = get_filename(path)

        producer = self.__get_element_from_template("producer")
        producer.attrib["id"] = str(index)
        producer.attrib["out"] = seconds_to_timestamp(clip.duration)
        producer.find(".//*[@name='length']").text = seconds_to_timestamp(clip.duration)
        producer.find(".//*[@name='resource']").text = filename
        producer.find(".//*[@name='shotcut:caption']").text = filename
        producer.find(".//*[@name='shotcut:detail']").text = filename

        # producers must be inserted above playlists and tractor to satisfy shotcut
        self.root.insert(4 + index, producer)
        self.producer_count = index + 1

        return index

    # def add_fade_in_producer(self, path):

    # def add_fade_out_producer(self, path):

    def add_playlist_entry(self, producer_number, starting_timestamp, ending_timestamp):
        video_playlist = self.root.find(".//*[@id='video_playlist']")

        entry = et.Element('entry')
        entry.attrib["producer"] = str(producer_number)
        entry.attrib["in"] = starting_timestamp
        entry.attrib["out"] = ending_timestamp

        video_playlist.append(entry)

    def write(self, path):
        et.ElementTree(self.root).write(path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

main()