
import matplotlib.pyplot as plt
import os
import time
import pandas as pd
import logging
from wrappers import calculate_time

# Functions
from scope_functions import *  # pylint: disable=unused-wildcard-import

# Configure loggin
# logging.basicConfig(
#     filename="logging/pandasscopeparser.log", level=logging.INFO)


class PandasScopeParser():
    # Constructor
    def __init__(self, scope_data, alpha_filter_on=False, rms=False, avg=False, *args, **kwargs):
        """ 
            Mandatory arguments:
            - scope_data : python dict-object or string object with filename (.alb, .isf or .ISF)
            - alpha_filter_on : whether or not alpha filter is applied (default to False)
            - rms : hether or not rms traces are generated (default to False)
            - avg : hether or not avg traces are generated (default to False)

            Kwargs:
            - alpha : float/decimal/double that is used alpha filter (default to 0.8)
            - rms_freq : base frequency to calculate rms value from (default to 50)
            - averaging_freq : base frequency to calculate average value from (default to 50)
            - rename_dict : default naming is according to CH? as given by scope_data, insert dict in format {"CH1": name1, "CH2": name2, ... } (default to None)
            - specify_rms : specify which trace(s) need rms trace(s) (default to None) [done after renaming! so use name1, name2, ...]
            - specify_avg : specify which trace(s) need avg trace(s) (default to None) [done after renaming! so use name1, name2, ...]

            Remarks:
            - rms is based on period basis (not half period)
            - when alpha_filter_on = True : real raw data is replaced by alpha filter data!
            - in case of .ISF or .isf : "CH?" is decimated out of basename, every file starting with basename is processed
            - if list: python list object if read by visa --> TODO: check and work out
        """
        # declare instance variables
        alpha = kwargs["alpha"] if "alpha" in kwargs.keys(
        ) else 0.8  # default 0.8 value
        # frequency defaults to 50
        rms_freq = kwargs["rms_freq"] if "rms_freq" in kwargs.keys() else 50
        averaging_freq = kwargs["averaging_freq"] if "averaging_freq" in kwargs.keys(
        ) else 50  # frequency defaults to 50
        specify_rms = kwargs["specify_rms"] if "specify_rms" in kwargs.keys(
        ) else None  # when None, all data traces are rmsed
        specify_avg = kwargs["specify_avg"] if "specify_avg" in kwargs.keys(
        ) else None  # when None, all data traces are avged
        rename_dict = kwargs["rename_dict"] if "rename_dict" in kwargs.keys(
        ) else None  # when None, do not rename anything
        # rename should be done before calculating rms and avg (making new traces)
        self.type = None
        # TODO: check if universal header is viable (different build up for tektronix/keysight)
        self.header = None
        self._isf_header = dict()  # scrapped if universal header is viable
        self._alb_header = dict()  # scrapped if universal header is viable
        self._list_header = None
        self.data = dict()  # dict with different channels supported
        self.time = None  # same dimension as data
        self.number_of_traces = None
        # returns length of data lists (and time list)
        self.length_of_data = None
        self.file_ext = None
        self.basename = None

        # determine data type to instance variables
        if type(scope_data) == str:
            self.type = "file"
            temp = os.path.splitext(scope_data)
            self.file_ext = temp[1]
            # always "CH?"" at the end of the file?
            self.basename = temp[0][:-
                                    3] if temp[1].lower() == ".isf" else temp[0]
        elif type(scope_data) == dict:
            self.type = "dict"
            self._list_header = args[0]
        else:
            raise AttributeError("No valid datatype given to the contstructor")

        # TODO: when loading file, you can use os.path to retrieve extension, this can then be used to determine parsing actions to be taken
        if self.type == "file" and self.file_ext.lower() == ".isf":
            if self.basename:
                applicable_files = []
                names = []
                directories = list(os.path.split(os.path.abspath(
                    self.basename))) if "/" in self.basename else None
                file = directories.pop()
                target_dir = "/".join(directories)
                for root, dirs, files in os.walk(target_dir):  # pylint: disable=unused-variable
                    for i in range(len(files)):
                        split = os.path.splitext(files[i])
                        if file in files[i]:
                            names.append(split[0].lstrip(file))
                            applicable_files.append(
                                target_dir + "/" + files[i])
                for x in range(len(applicable_files)):
                    temp = self._parse_isf(applicable_files[x])
                    self.data[f"{names[x]}"] = temp[1]
                    self._isf_header[f"{names[x]}"] = temp[0]
                    if not self.time:
                        self.time = temp[2]
                        self.length_of_data = len(self.time)
                self.number_of_traces = len(self.data)
            else:
                raise AttributeError(
                    "No basename was put in arguments which is needed")
        elif self.type == "file" and self.file_ext == ".alb":
            self._parse_alb(self.basename)
        elif self.type == "dict":
            self.data = scope_data
            x_incr = self._list_header["CH1"]["x_incr"]
            points = self._list_header["CH1"]["points"]
            self.time = list(x_incr * t for t in range(points))
        else:
            raise Exception("No type defined")

        # when done alpha filter is done on data, real raw data is overwritten!!! Not available any more after this point
        if alpha_filter_on:
            for k, v in self.data.items():
                self.data[k] = alpha_filter(v, alpha)

        # Make a pandas dataframe out of data
        self.df = pd.DataFrame({"time": self.time})
        for k, v in self.data.items():
            self.df[k] = v
        if rename_dict:
            self.df.rename(columns=rename_dict, inplace=True)

        if rms:
            for k, v in self.df.items():
                if specify_rms == None:
                    k_new = k + "_rms"
                    self.df[k_new] = rms_calc(self.time, v, rms_freq)
                elif str(k) in specify_rms:
                    k_new = k + "_rms"
                    self.df[k_new] = rms_calc(self.time, v, rms_freq)

        if avg:
            for k, v in self.df.items():
                if specify_avg == None:
                    k_new = k + "_avg"
                    self.df[k_new] = avg_calc(self.time, v, averaging_freq)
                elif str(k) in specify_avg:
                    k_new = k + "_avg"
                    self.df[k_new] = avg_calc(self.time, v, averaging_freq)

        # logging.info("File completed loading succesfully")
    # private methods

    # ISF
    def _parse_isf(self, filename):
        f = open(f"{filename}", "rb")
        header = []
        data = []
        chunk_reached = False
        points_designator = False
        nr_of_bits = 0
        counter = 0
        while True:
            chunk = f.read(1)
            if not chunk:
                break
            elif chunk_reached:
                # chunked_reached becomes True upon seeing "#" in the datastream
                if not points_designator:
                    # first byte after "#" contains and int that describes how many bytes are refering to the size
                    nr_of_bits = int(chunk.decode("utf8"))
                    points_designator = True
                else:
                    if counter < nr_of_bits:
                        # as long as the counter has not reached the nr_of_bits keep adding bytes to the info list
                        header.append(chunk.decode("utf8"))
                        counter += 1
                    else:
                        # everything else goes to the binary data list
                        data.append(chunk)
            elif chunk.decode("utf8", errors="ignore") == "#":
                # # is the designator in the .isf that starts a sequence to decrypt the binary data
                header.append(chunk.decode("utf8"))
                chunk_reached = True
            else:
                header.append(chunk.decode("utf8", "ignore"))
        f.close()
        header_list = "".join(header[:]).split(";")
        header_dict = self._get_header_dict(header_list)
        trace_data = self._parse_isf_data(data, header_dict)
        time_data = self._create_isf_time(trace_data, header_dict)
        return [header_dict, trace_data, time_data]

    def _get_header_dict(self, header_list):
        res = {"BYT_NR": None, "ENCODING": None, "BINARY_FORMAT": None, "BYT_OR": None, "BIT_NR": None, "WFID_channel": None, "WFID_coupling": None,
               "WFID_y_scale_number": None, "WFID_y_scale_unit": None, "WFID_x_scale_number": None, "WFID_x_scale_unit": None, "WFID_number_of_points": None,
               "NR_PT": None, "XINCR": None, "XZERO": None, "YMULT": None, "YOFF": None, "YZERO": None, "VSCALE": None, "HSCALE": None, "VPOS": None, "VOFFSET": None,
               "HDELAY": None}
        for e in header_list:
            res["BYT_NR"] = int(e[len(e)-1]) if "BYT_N" in e else res["BYT_NR"]
            res["ENCODING"] = e[6:] if "ENCDG" in e else res["ENCODING"]
            res["BINARY_FORMAT"] = e[7:] if "BN_FMT" in e else res["BINARY_FORMAT"]
            res["BYT_OR"] = e[7:] if "BYT_OR" in e else e[6:] if "BYT_OR" in e else res["BYT_OR"]
            if "BIT_N" in e:
                x = ""
                for i in range(len(e)-3, len(e)):
                    if e[i].isnumeric():
                        x = x + e[i]
                res["BIT_NR"] = int(x)
            if e.startswith("WFID"):
                x = e.lstrip('WFID "').rstrip('"').split(",")
                res["WFID_channel"] = x[0]
                res["WFID_coupling"] = x[1][1:3]
                temp = self._parse_isf_wfid(x[2])
                res["WFID_y_scale_number"] = temp[0]
                res["WFID_y_scale_unit"] = temp[1]
                temp = self._parse_isf_wfid(x[3])
                res["WFID_x_scale_number"] = temp[0]
                res["WFID_x_scale_unit"] = temp[1]
                if x[4].rstrip().endswith("points"):
                    num = ""
                    for i in x[4]:
                        if i.isnumeric():
                            num = num + i
                    res["WFID_number_of_points"] = int(num)
            if "NR_P" in e:
                if ":" in e:
                    pass
                elif "NR_PT" in e:
                    res["NR_PT"] = int(e[6:])
                else:
                    res["NR_PT"] = int(e[5:])
            res["XINCR"] = float(e[6:]) if "XINCR" in e else float(
                e[3:]) if "XIN" in e else res["XINCR"]
            res["XZERO"] = float(e[6:]) if "XZERO" in e else res["XZERO"]
            res["YMULT"] = float(e[6:]) if "YMULT" in e else float(
                e[4:]) if "YMU" in e else res["YMULT"]
            res["YOFF"] = float(e[5:]) if "YOFF" in e else float(
                e[4:]) if "YOF" in e else res["YOFF"]
            res["YZERO"] = float(e[6:]) if "YZERO" in e else res["YZERO"]
            res["VSCALE"] = float(e[7:]) if "VSCALE" in e else res["VSCALE"]
            res["HSCALE"] = float(e[7:]) if "HSCALE" in e else res["HSCALE"]
            res["VPOS"] = float(e[5:]) if "VPOS" in e else res["VPOS"]
            res["VOFFSET"] = float(e[8:]) if "VOFFSET" in e else res["VOFFSET"]
            res["HDELAY"] = float(e[7:]) if "HDELAY" in e else res["HDELAY"]
        return res

    def _parse_isf_wfid(self, arg):
        t = arg.lstrip(" ").rstrip(" ")
        number = ""
        unit_string = ""
        for x in t:
            if x.isnumeric() or x == ".":
                number = number + x
            else:
                unit_string = unit_string + x
        unit = unit_string.split("/")[0]
        return [float(number), unit]

    def _parse_isf_data(self, data, header_dict):
        """ return list(data_for_one_isf_file) """
        ret_data = []
        order = "big" if header_dict["BYT_OR"] == "MSB" else "little"
        if header_dict["BIT_NR"] == 16:
            for i in range(0, len(data), 2):
                sample = int.from_bytes(data[i]+data[i+1], order, signed=True)
                ret_data.append(
                    (sample - header_dict["YOFF"]) * header_dict["YMULT"])
        elif header_dict["BIT_NR"] == 8:
            for i in range(len(data)):
                ret_data.append(((int.from_bytes(
                    data[i], order, signed=True) - header_dict["YOFF"]) * header_dict["YMULT"]))
        return ret_data

    def _create_isf_time(self, data, header_dict):
        """ return list(time_data)
            returns the time data scale for this scope image """
        # in principle you can use header_dict to retrieve number of sample however len(data) seems safer to be sure
        return list(i * header_dict["XINCR"] for i in range(len(data)))

    # ALB
    def _parse_alb(self, basename):
        # declarations
        filename = basename + ".alb"
        setupname = basename + ".txt"
        header = []
        setup = None
        raw = None

        # opening .alb file for header information + data
        with open(filename, "rb") as file:
            while True:
                x = file.readline().decode("utf8").rstrip()
                if "HEADER_END" in x:
                    header.append(x)
                    raw = file.read()
                    break
                else:
                    header.append(x)
        self._alb_header = self._analyze_alb_header(header)
        setup = self._analyze_alb_setup(setupname)
        # print(setup)
        # .txt setup data with self._alb_header
        for x in setup.keys():
            for y in range(len(self._alb_header)):
                if x == self._alb_header[y]["name"]:
                    self._alb_header[y].update(setup[x])
        # print(self._alb_header)
        temp = self._analyze_alb_data(raw, self._alb_header)
        self._analyze_alb_setup(setupname)
        self.data = temp[0]
        self.time = temp[1]
        self.number_of_traces = len(self.data)
        self.length_of_data = len(self.time)

    def _analyze_alb_header(self, header):
        ret = []
        for x in header:
            if "TABLE_BEGIN" in x:
                temp_dict = dict()
                temp_dict["name"] = x.split('"')[1][-3:].upper()
            elif "TABLE_END" in x:
                ret.append(temp_dict)
            elif "COLUMN" in x:
                s = x.split("=")
                temp_dict["VALUE_BYTES"] = int(s[1][0])
                temp_dict["WIDTH_BITS"] = int(s[2])
            elif "=" in x:
                s = x.split("=")
                if s[1][len(s[1])-1].isnumeric():
                    if "." in s[1]:
                        temp_dict[s[0]] = float(s[1])
                    else:
                        temp_dict[s[0]] = int(s[1])
                else:
                    temp_dict[s[0]] = s[1].rstrip()
        return ret

    def _analyze_alb_data(self, data, header_dict):
        ret_list = dict()
        time_list = None
        for x in range(0, len(header_dict)):
            temp_list = []
            if header_dict[x]["WIDTH_BITS"] == 16:
                for i in range(header_dict[x]["NUM_ROWS"]):
                    start = (i*2 + x * header_dict[x]["NUM_ROWS"] * 2)
                    stop = (i*2 + x * header_dict[x]["NUM_ROWS"] * 2) + 2
                    # temp_list.append((int.from_bytes(data[start:stop], "big", signed=True) * header_dict[x]["Y_INC"] + header_dict[x]["Y_ORG"])*int(header_dict[x]["PROBE_SETUP"]))
                    temp_list.append((int.from_bytes(
                        data[start:stop], "big", signed=True) * header_dict[x]["Y_INC"] + header_dict[x]["Y_ORG"]))
                if not time_list:
                    time_list = list(
                        x * header_dict[0]["X_INC"] for x in range(len(temp_list)))
                ret_list[header_dict[x]["name"]] = temp_list
        return [ret_list, time_list]

    def _analyze_alb_setup(self, setupfile):
        temp = []
        ret = dict()
        # print(setupfile)
        try:
            with open(setupfile, "r") as file:
                for x in file.readlines():
                    if not x == "\n":
                        temp_list = list(
                            filter(lambda a: a != "", x.strip().split("  ")))
                        if temp_list[0].startswith("Ch"):
                            temp.append(temp_list)
            # print(len(temp))
            for e in temp:
                name = e[0].rstrip(":").replace(" ", "").upper()
                # print(name)
                if name not in ret.keys():
                    ret[name] = dict()
                if len(e) > 2:
                    ret[name]["STATE"] = e[1]
                    ret[name]["PER_DIV"] = e[2].rstrip("/")
                    ret[name]["UNIT"] = e[3][-1]
                    ret[name]["COUPLING"] = e[4].strip()
                    ret[name]["TERM"] = e[-1].strip()
                    # state = e[1]
                    # per_div = e[2].rstrip("/")
                    # unit = e[3][-1]
                    # coupling = e[4].strip()
                    # termination = e[-1].strip()
                    # temp_dict = {"STATE": state, "PER_DIV": per_div, "UNIT": unit, "COUPLING": coupling, "TERM": termination}
                if len(e) == 2:
                    ret[name]["PROBE_SETUP"] = int(
                        float(e[1].split(":")[0].rstrip()))
        except:
            FileNotFoundError("Setup file not saved")
        return ret

    # Getters
    def get_length_of_data(self):
        return self.length_of_data

    def get_trace_names(self):
        return list(self.data.keys())

    def get_trace(self, trace_key):
        """ gives trace data in a 1D list if your argument matches with a key, run "get_trace_names" if you want to get your options """
        try:
            return self.data[f"{trace_key}"]
        except KeyError:
            "This is not an existing key for this instance"

    def get_time(self):
        return self.time

    def get_number_of_traces(self):
        return self.number_of_traces

    def get_header(self):
        return self.header

    def get_type(self):
        return self.type


def main():
    # z = calculate_time(UniversalParser, "data_test/scope_96.alb")()
    x = calculate_time(PandasScopeParser)(
        "pylib/testing_files/tek0000CH1.isf", False, True)
    print(x.df.head(5))
    # fig, axs = plt.subplots(2, 2)
    # axs[0][0].plot(a.df.time, a.df.input_current, label = a.df.input_current.name)
    # axs[0][0].plot(a.df.time, a.df.input_current_rms, label = a.df.input_current_rms.name)
    # axs[0][1].plot(a.df.time, a.df.input_voltage, label = a.df.input_voltage.name)
    # axs[0][1].plot(a.df.time, a.df.input_voltage_rms, label = a.df.input_voltage_rms.name)
    # axs[1][0].plot(a.df.time, a.df.dc_voltage, label = a.df.dc_voltage.name)
    # axs[1][1].plot(a.df.time, a.df.led_current, label = a.df.led_current.name)
    # axs[1][1].plot(a.df.time, a.df.led_current_avg, label = a.df.led_current_avg.name)
    # fig.savefig("data_test/test.png")
    # fig.show()


if __name__ == "__main__":
    main()
