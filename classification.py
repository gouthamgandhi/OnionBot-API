from edgetpu.classification.engine import ClassificationEngine
from edgetpu.utils import dataset_utils
from PIL import Image
from threading import Thread, Event
from queue import Queue, Empty


import logging

logger = logging.getLogger(__name__)


class Classify(object):
    """Save image to file"""

    def __init__(self):

        self.tests = (
            {
                "pasta": {
                    "labels": "models/pasta.txt",
                    "model": "models/pasta.tflite",
                    "threshold": 0.8,
                }
            },
            {
                "sauce": {
                    "labels": "models/sauce.txt",
                    "model": "models/sauce.tflite",
                    "threshold": 0.8,
                }
            },
            {
                "pan_on_off": {
                    "labels": "models/pan_on_off.txt",
                    "model": "models/pan_on_off.tflite",
                    "threshold": 0.5,
                }
            },
        )

        self.quit_event = Event()
        self.file_queue = Queue()
        self.data = None

    def _worker(self):

        logger.info("Initialising upload worker")

        while True:
            try:  # Timeout raises queue.Empty

                image = self.file_queue.get(block=True, timeout=0.1)
                image = Image.open(image)

                output = {}

                for name, t in self.tests.items():

                    logger.info("Starting test %s " % (name))

                    engine = ClassificationEngine(t["model"])
                    labels = dataset_utils.read_label_file(t["labels"])
                    threshold = t["threshold"]

                    result = engine.classify_with_image(
                        image, top_k=1, threshold=threshold
                    )

                    logger.info(result)

                    output["t"] = {
                        "label": labels[result[0]],
                        "confidence": result[1],
                    }
                self.data = output

            except Empty:
                if self.quit_event.is_set():
                    logger.info("Quitting thread...")
                    break

    def start(self, file_path):
        logger.info("Calling start")
        self.file_queue.put(file_path)

    def join(self):
        logger.info("Calling join")
        self.file_queue.join()

    def launch(self):
        logger.info("Initialising worker")
        self.thread = Thread(target=self._worker, daemon=True)
        self.thread.start()

    def quit(self):
        self.quit_event.set()
        logger.info("Waiting for classification thread to finish uploading")
        self.thread.join()