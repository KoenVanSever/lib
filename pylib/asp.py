import re
import matplotlib.pyplot as plt
import os
import glob

# added because of annoying GLib warning in matplotlib (savefig)
import warnings
warnings.simplefilter("ignore")


class Params:
    def __init__(self, data):
        self.reload_data(data)

    def get_side_a(self):
        return self._a_data

    def get_side_b(self):
        return self._b_data

    def reload_data(self, data):
        self._data = data
        self._a_data = []
        self._b_data = []
        for l in self._data.split("\n"):
            if l.startswith("A side"):
                t = l.split(",")
                for x in t:
                    self._a_data.append(int(x.strip("Aside: "), 16))
            elif l.startswith("B side"):
                t = l.split(",")
                for x in t:
                    self._b_data.append(int(x.strip("Bside: "), 16))
            else:
                continue


class Rx:
    def __init__(self, data, arg1, arg2, **kwargs):
        self.threshold_level = kwargs["threshold_level"] if "threshold_level" in kwargs.keys(
        ) else 100
        self.test_mode = kwargs["test_mode"] if "test_mode" in kwargs.keys(
        ) else False
        self._arg1 = arg1
        self._arg2 = arg2
        self.reload_alc_data(data)

    def reload_alc_data(self, data):
        self._data = data
        self._alc_data = []
        self._adc_data_rx = []
        self._adc_data_50 = []
        self.alc_bit_array = []
        self.alc_strength_array_1 = []
        self.alc_strength_array_0 = []
        self.alc_noise_array = []

        for line in self._data.split("\n"):
            line.rstrip()
            if "/" in line:
                temp = line.split(" ")
                self._alc_data = temp
                for x in temp:
                    if re.search(r"[0-1]/.", x):
                        y = x.split("/")
                        if int(y[1]) < self.threshold_level:
                            self.alc_noise_array.append(int(y[1]))
                        else:
                            self.alc_bit_array.append(int(y[0]))
                            if y[0] == "0":
                                self.alc_strength_array_0.append(int(y[1]))
                            elif y[0] == "1":
                                self.alc_strength_array_1.append(int(y[1]))
                            else:
                                continue
            elif "," in line:
                try:
                    temp_data = list(map(lambda x: int(x), line.split(",")))
                    temp_data.pop(len(temp_data)-1)
                    if len(temp_data) > 400:
                        self._adc_data_50.append(temp_data)
                    elif len(temp_data) <= 400:
                        self._adc_data_rx.append(temp_data)
                    else:
                        continue
                except:
                    pass
            else:
                print(f"Useless line in command rx {self._arg1} {self._arg2}")

    def plot_adc_data_50(self, line_nr):
        # line_nr is starting from 1, not 0
        return self._plot_data(line_nr, self._adc_data_50, 50)

    def plot_adc_data_hf(self, line_nr):
        return self._plot_data(line_nr, self._adc_data_rx, "hf")

    def print_filter_value_50(self):
        res = []
        try:
            y = self._adc_data_50[0][0]
            for x in range(len(self._adc_data_50[0])):
                y = round((self._adc_data_50[0][x]
                           * (256-220) + y * 220) / 256, 3)
                res.append(y)
        except IndexError:
            "Something wrong with input"
        return res

    def plot_filter_value_50(self):
        res = [self.print_filter_value_50()]
        tot = []
        try:
            x = self._plot_data(0, res, "filt")
            tot.append(x)
        except:
            Exception("No filter data available")
        return tot

    def plot_adc_data_50_all(self):
        tot = []
        try:
            for i in range(len(self._adc_data_50)):
                x = self._plot_data((i), self._adc_data_50, 50)
                tot.append(x)
        except:
            Exception("No 50Hz data available")
        return tot

    def plot_adc_data_hf_all(self):
        tot = []
        try:
            for i in range(len(self._adc_data_rx)):
                x = self._plot_data((i), self._adc_data_rx, "hf")
                tot.append(x)
        except:
            Exception("No hf data available")
        return tot

    def return_alc_dict(self):
        return dict(threshold=self.threshold_level, count_noise=self.get_noise_count(), avg_noise=self.get_avg_noise(), avg_0=self.get_avg_alc_strength_0(),
                    avg_1=self.get_avg_alc_strength_1(), count_0=self.get_0_count(), count_1=self.get_1_count(), max_0=self.get_max_alc_0(), max_1=self.get_max_alc_1())

    def __str__(self):
        return f"""
        Treshold level used: {self.threshold_level}
        Average noise (count, average) : {self.get_noise_count()}, {self.get_avg_noise()}
        Bit 0 information (count, average, max) : {self.get_0_count()}, {self.get_avg_alc_strength_0()}, {self.get_max_alc_0()}
        Bit 1 information (count, average, max) : {self.get_1_count()}, {self.get_avg_alc_strength_1()}, {self.get_max_alc_1()}
        """

    # GETTERS

    def get_alc_strength_array_1(self):
        return self.alc_strength_array_1

    def get_alc_strength_array_0(self):
        return self.alc_strength_array_0

    def get_max_alc_0(self):
        try:
            return max(self.alc_strength_array_0)
        except Exception:
            "There was not ALC value above the threshold level"

    def get_max_alc_1(self):
        try:
            return max(self.alc_strength_array_1)
        except Exception:
            "There was not ALC value above the threshold level"

    def get_noise_array(self):
        return self.alc_noise_array

    def get_bit_array(self):
        return self.alc_bit_array

    def get_0_count(self):
        return self.alc_bit_array.count(0)

    def get_1_count(self):
        return self.alc_bit_array.count(1)

    def get_avg_alc_strength_1(self):
        return self._average_array(self.alc_strength_array_1, 0)

    def get_avg_alc_strength_0(self):
        return self._average_array(self.alc_strength_array_0, 0)

    def get_avg_noise(self):
        return self._average_array(self.alc_noise_array, 1)

    def get_noise_count(self):
        return len(self.alc_noise_array)

    def get_alc_threshold_level(self):
        return self.threshold_level

    # SETTERS

    def set_alc_threshold_level(self, thr):
        self.threshold_level = thr
        self.reload_alc_data(self._data)
        return self.threshold_level

    # Private functions

    def _average_array(self, array, rounding):
        try:
            return round(sum(array)/len(array), rounding)
        except ZeroDivisionError:
            "The array passed to the function has no data in it"

    def _plot_data(self, line_nr, array, type):
        if array == []:
            return "selected file has no adc data"
        elif len(array) < line_nr and array != []:
            return "no line available for this number"
        else:
            test = ""
            if self.test_mode:
                test = "test/"
            name = f"{test}plots/plot_{type}_l{line_nr}_{str(id(self))[-7:-1]}"
            plt.plot(array[line_nr-1])
            plt.title(f"{os.path.basename(name)}", color="#FF0000")
            plt.ylim((-50, 4146))
            plt.xlabel("Sample Number")
            plt.ylabel("ADC value")
            plt.grid()
            # plt.summer()
            plt.savefig(name)
            plt.close()
            return name


def main():
    #   PARAMS TEST    #

    # f = open("safeled_debug_app/test/params_data")
    # fl = f.read()
    # param = Params(fl)
    # f.close()
    # print(param.get_side_a())
    # print(param.get_side_b())

    #   RX TEST    #

    f = open("test/data_rx_1000_1")
    fl = f.read()  # pylint: disable=unused-variable
    f.close()
    f2 = open("test/data_rx_10_1000")
    fl2 = f2.read()
    f2.close()
    # rx_1 = Rx(fl, 1000, 1, threshold_level = 10, test_mode = True)
    rx_2 = Rx(fl2, 10, 1000, threshold_level=8, test_mode=True)
    files = glob.glob(f"{os.getcwd()}/test/plots/*.png")
    for x in files:
        os.remove(x)
    print(rx_2.plot_adc_data_50_all())
    print(rx_2.plot_adc_data_hf_all())
    print(rx_2.plot_filter_value_50())
    # print(rx_1.plot_adc_data_50_all())
    # print(rx_1.plot_adc_data_hf_all())
    # print(rx_1)
    # print(rx_1.return_alc_dict())
    # print(rx_2)
    # print(rx_2.return_alc_dict())


if __name__ == "__main__":
    main()
