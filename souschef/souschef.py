from requests import post
from time import sleep
from threading import Thread
import socket
import logging

# # Fix logging faliure issue
# for handler in logging.root.handlers[:]:
#     logging.root.removeHandler(handler)

# Initialise custom logging format
FORMAT = "%(relativeCreated)6d %(levelname)-8s %(name)s %(process)d %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)

ip_address = "192.168.0.78"

# testIP = "8.8.8.8"
# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# s.connect((testIP, 0))
# ip_address = s.getsockname()[0]

ip = "http://" + ip_address + ":5000/"


class SousChef(object):
    def __init__(self):
        self.latest_meta = {}
        self.stop_flag = False
        self.previous_message = "Previous message"
        self.current_message = "Current message"
        self.next_message = "Next message"

        self.step_ID = 1
        self.substep_ID = 1

    def _meta_worker(self):
        while True:
            data = {"action": "get_latest_meta"}
            r = post(ip, data)
            self.latest_meta = dict(r.json())
            sleep(0.1)

    def _worker(self):
        def _update_screen():
            step_ID = self.step_ID

            try:
                self.previous_message = dispatch_table[step_ID - 1]["message"]
            except KeyError:
                self.previous_message = "Onionbot is connected"

            try:
                self.current_message = dispatch_table[step_ID]["message"]
            except KeyError:
                print("hmmm")

            try:
                self.next_message = dispatch_table[step_ID + 1]["message"]
            except KeyError:
                self.next_message = "Recipe complete!"

        def _classify(args):

            model = args["model"]
            label = args["label"]
            logger.debug("Classifying Model %s | Label %s" % (model, label))

            meta = self.latest_meta
            try:
                data = meta["attributes"]["classification_data"]
                if data[model][label]["boolean"]:
                    logger.info("Classifier: " + model + " " + label + " returned true")

                    rolling_window = float(meta["attributes"]["interval"]) * 5
                    logger.info("Sleeping for %s seconds..." % (rolling_window))
                    sleep(rolling_window)
                    return True
            except KeyError:
                pass
            return False

        def _set_classifiers(args):
            value = args["value"]
            logger.info("Setting classifiers")
            data = {"action": "set_classifiers", "value": str(value)}
            post(ip, data)
            return True

        def _set_fixed_setpoint(args):
            value = args["value"]
            logger.info("Setting fixed_setpoint")
            data = {"action": "set_fixed_setpoint", "value": str(value)}
            post(ip, data)
            return True

        def _set_temperature_target(args):
            value = args["value"]
            logger.info("Setting temperature_target")
            data = {"action": "set_temperature_target", "value": str(value)}
            post(ip, data)
            return True

        def _set_hob_off():
            logger.info("Turning hob off")
            data = {"action": "set_hob_off"}
            post(ip, data)
            return True

        # Import recipe from file
        with open("recipes.py", "r") as file:
            data = file.read().replace("\n", "")
        dispatch_table = eval(data)

        while True:
            result = False
            logger.info("Step %s | Substep %s" % (self.step_ID, self.substep_ID))
            while result is False and self.stop_flag is False:
                result = False
                step_ID = self.step_ID
                substep_ID = self.substep_ID

                _update_screen()

                substep = dispatch_table[step_ID][substep_ID]

                arguments = substep.get("args")
                if arguments:
                    result = substep["func"](args=arguments)
                else:
                    result = substep["func"]()
                sleep(0.1)

            # Increment all substeps then increment steps
            if self.stop_flag is True:
                break
            elif self.substep_ID + 1 in dispatch_table[self.step_ID].keys():
                self.substep_ID += 1
            elif self.step_ID + 1 in dispatch_table.keys():
                self.step_ID += 1
                self.substep_ID = 1
            else:
                break  # Recipe is complete

    def next(self):
        logger.info("Next called")
        self.substep_ID = 1
        self.step_ID += 1

    def previous(self):
        logger.info("Previous called")
        self.substep_ID = 1
        self.step_ID -= 1

    def stop(self):
        logger.info("Stop called")
        self.stop_flag = True
        self.t.join()  # Wait for recipe to finish before quitting

    def run(self):
        self.t = Thread(target=self._worker, daemon=True)  # , args=(1,)
        self.t.start()
        m = Thread(target=self._meta_worker, daemon=True)  # , args=(1,)
        m.start()
