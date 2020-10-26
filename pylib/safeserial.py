#!/home/koenvs/anaconda3/envs/pygtk/bin/python
#/usr/bin/python3

import serial
import platform
#print(platform.system())

class SafeSerial(serial.Serial):
    def __init__(self, **kwargs):
        # baudrate = 115200, bytsize = 8, parity = serial.PARITY_NONE, stopbits = 1, timeout = 0.1
        default_port = "/dev/ttyUSB0" if platform.system() == "Linux" else "COM1"
        port = kwargs["port"] if "port" in kwargs.keys() else default_port
        baudrate = kwargs["baud"] if "baud" in kwargs.keys() else 115200
        bytesize = kwargs["bytesize"] if "bytesize" in kwargs.keys() else 8
        parity = kwargs["parity"] if "parity" in kwargs.keys() else serial.PARITY_NONE
        stopbits = kwargs["stopbits"] if "stopbits" in kwargs.keys() else 1
        timeout = kwargs["timeout"] if "timeout" in kwargs.keys() else 0.1 # in seconds
        # self._serialport = serial.Serial(self._port, self._baud, self._bytesize, self._parity, self._stopbits, self._timeout)
        super().__init__(port, baudrate, bytesize, parity, stopbits, timeout)

    def open_admin(self):
        self.__write_sl("open")
        self.__write_sl("passwd admin")
        ret_val = self.__read_sl()
        if "(3)" in ret_val:
            t = ret_val.split("\n")
            e = t.pop(len(t)-1)
            return(f"Terminal opened correctly on admin level\n{e}")
        else:
            return("Something went wrong, please try again and check connections!\n")

    def write_reg(self, command, no_newline = False):
        self.__write_sl(command, no_newline)
        return command

    def extra_return(self, i):
        #needed for trying to debug commands where you are prompted
        #try to refrain from using with HPC since return will trigger dumping of readout values
        msg = i*"\r".encode("utf8")
        # print(msg)
        self.write(msg)

    def read_print_buffer(self):
        #time.sleep(0.1)
        bytes_to_read = self.inWaiting()
        s = self.read(bytes_to_read)
        # print(s)
        #optional replace method if you don't like whitespace in the window
        return s.decode("utf8").replace("\n\r\n", "\n")

    def __read_sl(self, cmd_send = "foobar"):
        # NOT USED ANY MORE
        s = self.read_until("Chuck(3):>".encode("utf8"))
        self.reset_input_buffer()
        return s.decode("utf8") + " "

    def __write_sl(self, command, no_newline = False):
        if type(command) != str:
            raise TypeError
        if no_newline:
            msg = command.rstrip()
        else:
            msg = command.rstrip() + "\n"
        # print(msg.encode("utf8"))
        self.write(msg.encode("utf8"))

def main():
    ser = SafeSerial()
    # ser.write_sl("open")
    # ser.write_sl("passwd admin")
    # print(ser.read_sl(), end = "")
    ser.open_admin()
    #ser.write_print("")

if __name__ == '__main__': main()
