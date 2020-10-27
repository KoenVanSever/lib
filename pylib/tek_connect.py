import pyvisa as visa
from pathlib import Path
import matplotlib.pyplot as plt

CHANNELS = ["CH1", "CH2", "CH3", "CH4"]


class TekConnection():
    def __init__(self, resource_name, channels=CHANNELS):
        self.instr = visa.ResourceManager().open_resource(resource_name)
        self.channels = channels
        print("connection opened: {}".format(self.instr.query("*IDN?")))

    def generate_isf(self, name):
        for chan in self.channels:
            self.instr.write(":DATA:ENC {}".format("RIB"))
            self.instr.write(f":DATA:SOURCE {chan}")
            fb = self.instr.query(":DATA:SOURCE?").rstrip().split(" ")[1]
            print(f"Getting data for {fb}: ", end="")
            self.instr.write("CURV?")
            data = self.instr.read_raw()
            header = self.instr.query(":WFMPRE?").rstrip() + ";"
            with open(f"{name}_{chan}.isf", "wb") as f:
                f.write(header.encode())
                f.write(data)
            print("done")

        # * SETTERS

    def set_encoding(self, res):
        self.instr.write(":DATA:ENC {}".format(res))
        fb = self.instr.query(":DATA:ENC?")
        return fb

    # * GETTERS
    def get_encoding(self):
        fb = self.instr.query(":DATA:ENC?")
        return fb


def main():
    conn = TekConnection("TCPIP0::192.168.2.33::INSTR")
    # print(conn.set_encoding("SRI"))
    conn.generate_isf("data_test/test")


if __name__ == "__main__":
    main()
