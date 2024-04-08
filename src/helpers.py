from datetime import datetime
import os


def get_timestamp_from_file(filepath):
    filename = filepath.split("\\")[-1].split(".")[0]
    templates = {"obs_dt_template": "%Y-%m-%d %H-%M-%S",
                "android_template": "VID_%Y%m%d_%H%M%S"}
    #import ipdb; ipdb.set_trace()
    for t in templates.values():
        try:
            dto = datetime.strptime(filename, t)
            print(f"using {t}")
            return int(dto.timestamp())
        except:
            continue
    print("Cannot parse time from filename. Using file creation time")
    return int(os.path.getmtime(filepath))

def generate_readable_timestamp(timestamp):
    time_string = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H-%M-%S')
    return time_string

def generate_standard_timestamp(timestamp):
    #2024-03-03T17:06:23.000Z
    time_string = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return time_string