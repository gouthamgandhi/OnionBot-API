import json
from cloud import Cloud
from os import makedirs, path
from datetime import datetime
from collections import Counter

import logging

logger = logging.getLogger(__name__)

cloud = Cloud()

PATH = path.dirname(__file__)
BUCKET = cloud.bucket


class Data:
    def __init__(self):
        self.camera_filepath = None
        self.thermal_filepath = None
        self.thermal_history_filepath = None
        self.meta_filepath = None
        self.timer = datetime.now()

    def start_session(self, session_ID, measurement_ID, label):

        # Labels file creation
        labels_file_path = f"{PATH}/{BUCKET}/{session_ID}/camera/labels.csv"

        if not path.isfile(labels_file_path):
            with open(labels_file_path, "w") as file:
                file.write("image_path[,label]\n")
                file.close()

        label_list = []
        with open(labels_file_path, "r") as file:
            line = file.readline()  # Deliberately skip header line!
            while line:
                line = file.readline()
                label = ",".join(line.split(",")[1:])  # Isolate labels
                label = label.strip("\n")
                label_list.append(label)

        label_count = dict(Counter(label_list))
        label_count.pop("", None)  # Remove empty labels

        self.label_count = label_count

    def generate_file_data(self, session_ID, timer, measurement_ID, label):
        """Generate file_data for local and cloud storage for all file types"""

        file_data = {}
        time_stamp = timer.strftime("%Y-%m-%d_%H-%M-%S-%f")

        # Camera filepath
        new_path = f"{PATH}/{BUCKET}/{session_ID}/camera/{label}"
        makedirs(new_path, exist_ok=True)
        filename = f"{session_ID}_{str(measurement_ID).zfill(5)}_{time_stamp}_camera_{label}.jpg"
        file_data["camera_file"] = f"{new_path}/{filename}"

        if not session_ID:
            file_data["label_file"] = None
            file_data["label_count"] = None
        else:
            # Update labels file
            labels_file_path = f"{PATH}/{BUCKET}/{session_ID}/camera/labels.csv"

            with open(labels_file_path, "a") as file:
                file.write(
                    f"gs://{BUCKET}/{session_ID}/camera/{label}/{filename},{label}\n"
                )
                file.close()

            file_data["label_file"] = labels_file_path

            # Increment labels counter
            with self.label_count[label] as label_entry:
                if label_entry:
                    label_entry += 1
                    self.label_count[label] = label_entry
                else:
                    self.label_count[label] = 1

            # Convert labels counter into json table form for web client
            label_count_output = []
            for key, value in self.label_count.items():
                dictionary = {}
                dictionary["label"] = key
                dictionary["count"] = value
                label_count_output.append(dictionary)
            file_data["label_count"] = label_count_output

        # Thermal filepath
        new_path = f"{PATH}/{BUCKET}/{session_ID}/thermal/{label}"
        makedirs(new_path, exist_ok=True)
        filename = f"{session_ID}_{str(measurement_ID).zfill(5)}_{time_stamp}_thermal_{label}.jpg"
        file_data["thermal"] = f"{new_path}/{filename}"

        # Meta filepath
        new_path = f"{PATH}/{BUCKET}/{session_ID}/meta/{label}"
        makedirs(new_path, exist_ok=True)
        filename = f"{session_ID}_{str(measurement_ID).zfill(5)}_{time_stamp}_meta_{label}.json"
        file_data["meta"] = f"{new_path}/{filename}"

        return file_data

    def generate_meta(
        self,
        session_ID,
        timer,
        measurement_ID,
        label,
        file_data,
        thermal_data,
        control_data,
    ):
        """Generate metadata to be parsed by portal"""

        interval = round((timer - self.timer).total_seconds(), 1)
        self.timer = timer
        time_stamp = timer.strftime("%Y-%m-%d_%H-%M-%S-%f")

        camera_filepath = cloud.get_public_path(file_data["camera_file"])
        thermal_filepath = cloud.get_public_path(file_data["thermal"])

        data = {
            "type": "meta",
            "id": f"{session_ID}_{measurement_ID}_{str(time_stamp)}",
            "attributes": {
                "session_ID": session_ID,
                "interval": interval,
                "label": label,
                "measurement_ID": measurement_ID,
                "time_stamp": time_stamp,
                "label_count": file_data["label_count"],
                "camera_filepath": camera_filepath,
                "thermal_filepath": thermal_filepath,
                "temperature": thermal_data["temperature"],
                "thermal_history": thermal_data["thermal_history"],
                "servo_setpoint": control_data["servo_setpoint"],
                "servo_setpoint_history": control_data["servo_setpoint_history"],
                "servo_achieved": control_data["servo_achieved"],
                "servo_achieved_history": control_data["servo_achieved_history"],
                "temperature_target": control_data["temperature_target"],
                "pid_enabled": control_data["pid_enabled"],
                "p_coefficient": control_data["p_coefficient"],
                "i_coefficient": control_data["i_coefficient"],
                "d_coefficient": control_data["d_coefficient"],
                "p_component": control_data["p_component"],
                "i_component": control_data["i_component"],
                "d_component": control_data["d_component"],
            },
        }

        # # Remove dictionary elements with 'None' type
        # attributes = data.get("attributes")
        # cleaned_data = {
        #     key: value for key, value in attributes.items() if value is not None
        # }
        # cleaned_data = {"attributes": cleaned_data}
        # data.update(cleaned_data)

        # logger.debug(data)

        with open(file_data["meta"], "w") as write_file:
            json.dump(data, write_file)

        return data

    def generate_labels(self):
        """Generate labels for live labelling functionality"""

        data = {
            "type": "labels",
            "attributes": {
                "Onion": {
                    "0": "Discard",
                    "1": "Raw",
                    "2": "Browning",
                    "3": "Brown",
                    "4": "Overcooked",
                },
                "Water": {
                    "0": "Discard",
                    "1": "Not boiling",
                    "2": "Simmering",
                    "3": "Boiling",
                },
            },
        }

        return data
