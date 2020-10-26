
import matplotlib.pyplot as plt
import pandas as pd
import logging
from pathlib import Path
from wrappers import calculate_time
from scope_functions import rms_calc, avg_calc, alpha_filter
from datetime import datetime as dt

# Configure loggin
FILE_DIR = Path(__file__).parent.resolve()
logging.basicConfig(
    filename=Path(FILE_DIR, "scopeparser.log"), format="%(asctime)s %(message)s", level=logging.INFO)


class ScopeParser():
    # Constructors
    @classmethod
    def from_isf(cls, path, channels=["CH1", "CH2", "CH3", "CH4"], *args, **kwargs):
        entry_type = "isf"
        """
        Parser .isf or .ISF file(s) into a ScopeParser-object, looks for "sibling" files in parent directory only

        Args:
            path (Path(Windows or Posix)): relative or absolute path of (one of) the file(s)
            channels (list): channels that will be used (defaults to all 4 regular channels)

        Returns:
            ScopeParser-object: [description]
        """
        absolute_path = path.resolve()  # ensure absolute scope
        parent_path = absolute_path.parent
        extension = absolute_path.suffix
        basename = absolute_path.name.rstrip(extension)[:-3]
        files = []
        for x in channels:
            temp = Path(parent_path, f"{basename}{x}{extension}")
            if temp.exists():
                files.append(temp)
            else:
                print(f"{temp} is not found and is ignored")
                logging.info(f"{temp} not found")
        if len(files) == 0:
            logging.warn(
                "Tried to make ScopeParser object without target files present")
            raise AttributeError(
                "None of the channels were found on this path!")
        return cls(entry_type, files=files, *args, **kwargs)

    @classmethod
    def from_alb(cls, path):
        entry_type = "alb"

    @classmethod
    def from_dict(cls, obj):
        pass

    def __init__(self, entry_type, *args, **kwargs):
        self.entry_type = entry_type
        # - determine entry type and act upon them
        if entry_type in ["isf", "alb"]:
            files = kwargs["files"] if "files" in kwargs.keys() else None
        elif entry_type == "dict":
            data = kwargs["data"] if "data" in kwargs.keys() else None
        else:
            raise AttributeError("Please provide valid entry_type")

        # - analyse keyword arguments
        alpha = kwargs["alpha"] if "alpha" in kwargs.keys() else 0.8
        rms_freq = kwargs["rms_freq"] if "rms_freq" in kwargs.keys() else 50
        averaging_freq = kwargs["averaging_freq"] if "averaging_freq" in kwargs.keys(
        ) else 50
        specify_rms = kwargs["specify_rms"] if "specify_rms" in kwargs.keys(
        ) else None
        specify_avg = kwargs["specify_avg"] if "specify_avg" in kwargs.keys(
        ) else None
        rename_dict = kwargs["rename_dict"] if "rename_dict" in kwargs.keys(
        ) else None
        alpha_filter_on = kwargs["alpha_filter_on"] if "alpha_filter_on" in kwargs.keys(
        ) else False
        rms = kwargs["rms"] if "rms" in kwargs.keys() else False
        avg = kwargs["avg"] if "avg" in kwargs.keys(
        ) else False
        # ! rename should be done before calculating rms and avg (making new traces)

        # - create dataframe
        self.df = pd.DataFrame()
        time_list = []
        if self.entry_type == "isf" and files:
            first = files[0].name.rstrip(files[0].suffix)[-3:]
            temp = self._parse_isf(files[0])
            self.df["time"] = temp[1]
            time_list = temp[1]
            self.df[first] = temp[0]
            if len(files[1:]) != 0:
                for file in files[1:]:
                    n = file.name.rstrip(file.suffix)[-3:]
                    self.df[n] = self._parse_isf(files[0], False)
        elif self.entry_type == "alb" and files:
            pass

        if rename_dict:
            self.df.rename(columns=rename_dict, inplace=True)

        # when done alpha filter is done on data, real raw data is overwritten!!! Not available any more after this point
        if alpha_filter_on:
            for k, v in self.data.items():
                self.data[k] = alpha_filter(v, alpha)

        # Make a pandas dataframe out of data

        if rms:
            for k, v in self.df.items():
                if specify_rms == None:
                    k_new = k + "_rms"
                    self.df[k_new] = rms_calc(time_list, v, rms_freq)
                elif str(k) in specify_rms:
                    k_new = k + "_rms"
                    self.df[k_new] = rms_calc(time_list, v, rms_freq)

        if avg:
            for k, v in self.df.items():
                if specify_avg == None:
                    k_new = k + "_avg"
                    self.df[k_new] = avg_calc(
                        time_list, v, averaging_freq)
                elif str(k) in specify_avg:
                    k_new = k + "_avg"
                    self.df[k_new] = avg_calc(
                        time_list, v, averaging_freq)

    # * PRIVATE

    # ISF
    def _parse_isf(self, filename, time_parse=True):
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
        if time_parse:
            time_data = self._create_isf_time(trace_data, header_dict)
            return [trace_data, time_data]
        else:
            return trace_data

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

    def get_number_of_traces(self):
        return self.number_of_traces

    def get_header(self):
        return self.header

    def get_type(self):
        return self.type


def main():

    obj = calculate_time(ScopeParser.from_isf)(
        Path(".", "pylib", "testing_files", "tek0000CH1.isf"), rms=True)
    print(obj.df.head(5))


if __name__ == "__main__":
    main()
