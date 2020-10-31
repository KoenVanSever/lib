#!/home/koenvs/anaconda3/envs/pygtk/bin/python
# /usr/bin/python3

import serial
import platform
import time


class SafeSerial(serial.Serial):
    def __init__(self, **kwargs):
        # /i DEFAULTS: baudrate = 115200, bytsize = 8, parity = serial.PARITY_NONE, stopbits = 1, timeout = 10
        # /i DEFAULT PORTS: /dev/ttyUSB0 on linux system, "COM1" on windows
        default_port = "/dev/ttyUSB0" if platform.system() == "Linux" else "COM1"
        port = kwargs["port"] if "port" in kwargs.keys() else default_port
        baudrate = kwargs["baud"] if "baud" in kwargs.keys() else 115200
        bytesize = kwargs["bytesize"] if "bytesize" in kwargs.keys() else 8
        parity = kwargs["parity"] if "parity" in kwargs.keys(
        ) else serial.PARITY_NONE
        stopbits = kwargs["stopbits"] if "stopbits" in kwargs.keys() else 1
        timeout = kwargs["timeout"] if "timeout" in kwargs.keys(
        ) else 10  # in seconds
        super().__init__(port, baudrate, bytesize, parity, stopbits, timeout)

    def open_admin(self):
        self.write_command("open")
        self.write_command("passwd admin")
        time.sleep(0.05)
        response = self.read(self.inWaiting())
        try:
            response_decode = response.decode("utf8")
        except UnicodeDecodeError:
            return "UnicodeDecodeError: meaning invalid UTF8/ASCII char, please check connections and try again\n"
        else:
            if "(3)" in response_decode:
                e = response_decode.split("\r\n\r\n").pop()
                return f"Terminal opened correctly on admin level\n{e}"
            else:
                return "Opened terminal on admin level not detected: please check connections and try again\n"

    def write_command(self, command, no_newline=False, return_instead_of_newline=False):
        """ 
            Parameters: 
                command - data to send (string format), no_newline - omits newline addition (bool: default false)
            Returns:
                number of bytes send (int)
            Raises:
                TypeError - if command is not the string type (convert to string before passing)
                SerialTimeoutException - if timeout configured and write time exceeded
            Description:
                Command in regular string format with no special characters (function handles adding \\n, encoding and writing)
                Writing to safeled serial port, take care with \\r!
                On HPC products this is handled by converter as signal to start dumping measurement values on serial port.
        """
        if type(command) != str:
            raise TypeError
        if return_instead_of_newline:
            msg = command.rstrip() + "\r"
        elif no_newline:
            msg = command.rstrip()
        else:
            msg = command.rstrip() + "\n"
        # print(msg.encode("utf8"))
        return self.write(msg.encode("utf8"))

    def read_inWaiting(self):
        # time.sleep(0.1)
        bytes_to_read = self.inWaiting()
        s = self.read(bytes_to_read)
        # print(s)
        # optional replace method if you don't like whitespace in the window
        return s.decode("utf8").replace("\n\r\n", "\n")

    def read_to_next_entry(self, command, dump_end=b"\r\n\r\n"):
        self.write_command(command)
        response = self.read_until(dump_end)
        try:
            response_decode = response.decode("utf8")
        except UnicodeDecodeError:
            return "UnicodeDecodeError: meaning invalid UTF8/ASCII char, please check connections and try again\n"
        else:
            return response_decode


def main():
    ser = SafeSerial()
    print(ser.open_admin())
    print(ser.read_to_next_entry("asp off"))
    print(ser.read_to_next_entry("rx 1 100"))


if __name__ == '__main__':
    main()
