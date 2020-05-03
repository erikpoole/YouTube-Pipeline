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
        if len(noisy_sections) < 2:
            # handle addition of two filters to one clip
            continue

        first_section = noisy_sections.pop(0)
        first_producer = Producer(path, mlt_file.get_next_producer_id())
        first_producer.add_filter(mlt_file.get_next_filter_id(), "fade_in", first_section[0], first_section[0] + 1)
        mlt_file.add_producer(first_producer)

        middle_producer = Producer(path, mlt_file.get_next_producer_id())
        mlt_file.add_producer(middle_producer)

        last_section = noisy_sections.pop()
        final_producer = Producer(path, mlt_file.get_next_producer_id())
        final_producer.add_filter(mlt_file.get_next_filter_id(), "fade_out", last_section[1] - 1, last_section[1])
        mlt_file.add_producer(final_producer)

        mlt_file.add_playlist_entry(first_producer.id, first_section[0], first_section[1])
        for section in noisy_sections:
            mlt_file.add_playlist_entry(middle_producer.id, section[0], section[1])
        mlt_file.add_playlist_entry(final_producer.id, last_section[0], last_section[1])
    
    mlt_file.write(os.path.join(output_path, date.today().strftime("%b-%d-%Y.mlt")))

def move_files(original_directory, new_directory):
    original_names = os.listdir(original_directory)
    original_paths = [os.path.join(original_directory, original_name) for original_name in original_names]
    original_paths.sort(key=lambda original_path: os.path.getctime(original_path))

    new_paths = []
    for index, original_path in enumerate(original_paths):
        new_path = os.path.join(new_directory, str(index) + ".mp4")
        # TODO change to shutil.move when pipeline is finished
        shutil.copy(original_path, new_path)
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
            continue
        if noisy_start >= 0 and not is_noisy(chunk):
            if noisy_end < 0:
                # if was noisy and now isn't - set noisy_end
                noisy_end = index
                continue
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

    ending_chunk = end + SILENCE_PADDING_CHUNKS
    ending_second = chunk_index_to_seconds(ending_chunk)
    if ending_second > seconds_upper_bound:
        ending_second = seconds_upper_bound

    sections.append([starting_second, ending_second])

def chunk_index_to_seconds(index):
    return index * CHUNK_DURATION

def seconds_to_timestamp(seconds):
    partial_seconds = seconds - int(seconds)
    formatted_seconds = '{:.3f}'.format(partial_seconds).lstrip('0')
    return "%s%s" % (time.strftime("%H:%M:%S", time.gmtime(seconds)), formatted_seconds)

def get_filename(path):
    return path.split("/")[-1]

def get_element_from_template(name):
    path = "./xml_templates/" + name + ".xml"
    tree = et.parse(path, et.XMLParser(remove_blank_text=True))
    return tree.getroot()

class MLTFile:
    def __init__(self):
        self.root = get_element_from_template("skeleton")
        self.producer_count = 0
        self.filter_count = 0
    
    def get_next_producer_id(self):
        return self.__get_next_id("producer_count")
    
    def get_next_filter_id(self):
        return self.__get_next_id("filter_count")

    def __get_next_id(self, id_type):
        id = getattr(self, id_type)
        setattr(self, id_type, id + 1)
        return str(id)

    def add_producer(self, producer):
        # producers must be inserted above playlists and tractor to satisfy shotcut
        self.root.insert(3 + self.producer_count, producer.root)

    def add_playlist_entry(self, producer_number, starting_second, ending_second):
        video_playlist = self.root.find(".//*[@id='video_playlist']")

        entry = et.Element('entry')
        entry.attrib["producer"] = str(producer_number)
        entry.attrib["in"] = seconds_to_timestamp(starting_second)
        entry.attrib["out"] = seconds_to_timestamp(ending_second)

        video_playlist.append(entry)

    def write(self, path):
        et.ElementTree(self.root).write(path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

class Producer:
    def __init__(self, path, id):
        duration = VideoFileClip(path, audio_fps=AUDIO_FPS).duration
        filename = get_filename(path)

        root = get_element_from_template("producer")
        root.attrib["id"] = id
        root.attrib["out"] = seconds_to_timestamp(duration)
        root.find(".//*[@name='length']").text = seconds_to_timestamp(duration)
        root.find(".//*[@name='resource']").text = filename
        root.find(".//*[@name='shotcut:caption']").text = filename
        root.find(".//*[@name='shotcut:detail']").text = filename

        self.root = root
        self.id = id
        self.duration = duration
        self.filename = filename

    def add_filter(self, id, filter_type, starting_second, ending_second):
        filter_root = get_element_from_template("filter")
        filter_root.attrib["id"] = id
        filter_root.attrib["in"] = seconds_to_timestamp(starting_second)
        filter_root.attrib["out"] = seconds_to_timestamp(ending_second)

        if filter_type == "fade_in":
            self.__set_filter_to_fade_in(filter_root)
        elif filter_type == "fade_out":
            self.__set_filter_to_fade_out(filter_root)
        else:
            print("invalid filter selected")
            return

        self.root.append(filter_root)

    def __set_filter_to_fade_in(self, filter_root):
        filter_root.find(".//*[@name='level']").text = "0=0; 30=1"
        filter_root.find(".//*[@name='mlt_service']").text = "brightness"
        filter_root.find(".//*[@name='shotcut:filter']").text = "fadeInBrightness"

    def __set_filter_to_fade_out(self, filter_root):
        filter_root.find(".//*[@name='level']").text = "0=1; 30=0"
        filter_root.find(".//*[@name='mlt_service']").text = "brightness"
        filter_root.find(".//*[@name='shotcut:filter']").text = "fadeOutBrightness"

main()