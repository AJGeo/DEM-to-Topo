import os


def add_file_name_marker_tif(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.tif'


def add_file_name_marker_shp(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.shp'


def add_file_name_marker_prj(scr_filename, tag):
    scr_filename_split = os.path.splitext(os.path.basename(scr_filename))
    return scr_filename_split[0] + tag + '.prj'


def print_dot():
    print('.', end="")
