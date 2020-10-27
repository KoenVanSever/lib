import pyvisa as visa
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

CHANNELS = ["CHAN1", "CHAN2", "CHAN3", "CHAN4"]

class AgilentConnection():
    FORMAT = {0: "BYTE", 1: "WORD", 4: "ASCII"}
    TYPE = {0: "NORMAL", 1: "PEAK", 2: "AVG"}
    DICT_KEYS = ["format", "type", "points", "count", "xincr", "xorigin", "xref", "yincr", "yorigin", "yref"]

    def __init__(self, resource_name, channels=CHANNELS):
        self.instr = visa.ResourceManager().open_resource(resource_name)
        self.instr.timeout = 1000
        self.channels = channels
        print("connection opened: {}".format(self.instr.query("*IDN?")))

    def generate_data_df(self):
        self.df = pd.DataFrame()
        for chan in self.channels:
            self.instr.write(f":WAVEFORM:SOURCE {chan}")
            print("Selected channel: {}".format(self.instr.query(":WAVEFORM:SOURCE?")), end = "")
            self.instr.write(":WAVEFORM:FORMAT WORD")
            self.instr.write(":WAVEFORM:TYPE NORMAL")
            try:
                self.instr.write(":WAVEFORM:POINTS:MODE MAX")
                # self.instr.write(":WAVEFORM:POINTS 2000000")
                # print(self.instr.query(":WAVEFORM:POINTS?"))
                preamble = [float(x) if "." in x or "E" in x else int(x) for x in self.instr.query(":WAV:PRE?").split(",")]
                pre_dict = dict(zip(self.DICT_KEYS, preamble))
                pre_dict["format"] = self.FORMAT[pre_dict["format"]] if pre_dict["format"] in self.FORMAT.keys() else pre_dict["format"]
                pre_dict["type"] = self.TYPE[pre_dict["type"]] if pre_dict["type"] in self.TYPE.keys() else pre_dict["type"]
                endian_big = True if "MSB" in self.instr.query(":WAV:BYT?") else False
                data = self.instr.query_binary_values(":WAVEFORM:DATA?", is_big_endian=endian_big, datatype="H")
                self.df[f"{chan}"] = [(x - pre_dict["yref"]) * pre_dict["yincr"] + pre_dict["yorigin"] for x in data]
                if not "time" in self.df.index:
                   self.df["time"] = [x * pre_dict["xincr"] for x in range(pre_dict["points"])]
            except visa.VisaIOError:
                print(f"Error loading {chan}")
            else:
                print(f"{chan} loaded correctly")
        # return self.df

    def save_screen_png(self, name):
        self.instr.write("")

def main():
    conn = AgilentConnection('USB0::0x0957::0x1734::MY44001922::INSTR', channels=["CHAN4"])
    conn.generate_data_df()



if __name__ == "__main__":
    main()