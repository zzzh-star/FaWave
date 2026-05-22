import sys
import os
import time
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.workers.acquisition_worker import AcquisitionWorker
from src.data.data_buffer import DataBuffer
from src.data.data_recorder import DataRecorder
import json

def test():
    with open('../config/default_config.json', 'r') as f:
        config = json.load(f)

    buf = DataBuffer()
    rec = DataRecorder()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test")
    worker = AcquisitionWorker(config, buf, rec, logger)

    worker.set_connection_params("Mock", "0.0.0.0", 0)
    worker.start()

    for i in range(12):
        time.sleep(1)
        data = buf.get_data()

        status = data[9]
        fx = data[6][-1] if data[6] else 0.0
        print(f"t={i}.0s status={status} Fx={fx}")

    worker.request_force_zero()
    print("Requested manual zeroing.")
    time.sleep(2)

    data = buf.get_data()
    print(f"t=14.0s status={data[9]} Fx={data[6][-1] if data[6] else 0.0}")

    worker.stop()
    print("Test finished.")

if __name__ == "__main__":
    test()
