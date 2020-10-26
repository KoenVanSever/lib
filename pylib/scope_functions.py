import math

def min_max(l_data):
    return (min(l_data), max(l_data))

def voltsec_product_old(l_time, l_data, freq):
    """ Generates a running voltsecond product where the refresh time is depending on frequency of the mains """
    # TODO: optimize function to be not so computational heavy (look at RMS function for inspiration)
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    time_step = 1 / freq / 2 
    nr_samples = int(time_step / (l_time[1] - l_time[0]))
    absolute = [abs(l_data[x]) for x in range(len(l_data))]
    accum = []
    for i in range(len(absolute)):
        if i >= (len(absolute) - 1):
            i = len(absolute)-2
        res_accum = (absolute[i+1]+absolute[i])/2*(l_time[i+1]-l_time[i])
        accum.append(res_accum)
    ret = []
    for i in range(len(accum)):
        nr = nr_samples if i >= nr_samples else i
        x = sum(accum[(i-nr) : (i+1)])
        ret.append(round(x, 2))
    return ret

def vs_help(nr_samples):
    x = 0
    while x < nr_samples:
        pass

def voltsec_product(l_time, l_data, freq, half_per = True):
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    freq = freq * 2 if half_per else freq
    time_step = 1 / freq
    nr_samples = int(time_step / (l_time[1] - l_time[0]))
    vs = [(abs(l_data[x]) + abs(l_data[x - 1 if x != 0 else 0]))/2 * (l_time[1] - l_time[0]) for x in range(len(l_data))]
    vs[0] = (abs(l_data[1]) + abs(l_data[0]))/2 * (l_time[1] - l_time[0])
    ret = []
    for i in range(len(vs)):
        nr = nr_samples if i >= nr_samples else i
        x = sum(vs[(i-nr) : (i+1)])
        ret.append(round(x, 2))
    return ret

def voltsec_product_total(l_time, l_data):
    """ Returns the volt second product of the entire trace (in float) """
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    absolute = [abs(l_data[x]) for x in range(len(l_data))]
    ret = sum(absolute)/(l_time[-1] - l_time[0])
    return ret

# old rms_calc_function: computational heavy so passes now when used, code still present
def rms_calc_old(l_time, l_data, freq):
    # """ OLD RMS METHOD, please use rms_calc_old (way more efficent!) """
    # l_time = list(l_time) # list objects calculates faster than Series object
    # l_data = list(l_data) # list objects calculates faster than Series object
    # time_step = 1 / freq
    # nr_samples = int(time_step / (l_time[1] - l_time[0]))
    # squared = [pow(l_data[x], 2) for x in range(len(l_data))]
    # accum = []
    # for i in range(len(squared)):
    #     nr = nr_samples if i >= nr_samples else i
    #     res_accum = sum(squared[(i-nr) : (i+1)]) / len(squared[(i-nr) : (i+1)])
    #     x = math.sqrt(res_accum)
    #     accum.append(x)
    # return accum
    pass

def rms_calc(l_time, l_data, freq, half_per = False):
    """ applies RMS calculation on a data trace, this is done on a period basis.
        For a half period basis, please multiply freq by 2 """
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    freq = freq * 2 if half_per else freq
    time_step = 1 / freq
    nr_samples = int(time_step / (l_time[1] - l_time[0]))
    incr = 0
    accum = []
    test = 0
    squared = [pow(l_data[x], 2) for x in range(len(l_data))]
    for i in range(len(l_data)):
        if incr < nr_samples:
            test = test + squared[i]
            accum.append(math.sqrt(test/(i+1)))
            incr += 1
        else:
            test = test - squared[i-nr_samples] + squared[i]
            accum.append(math.sqrt(test/nr_samples))
    return accum

def avg_list(l):
    """ Returns the overall average of all numbers in list 'l' """
    return sum(l)/len(l)
# avg_list_lambda = lambda x: sum(x)/len(x)

def alpha_filter(l, alpha):
    """ applies alpha filter on a data trace """
    l = list(l) # list objects calculates faster than Series object
    y = l[0]
    res = []
    for x in range(len(l)):
        y = alpha * y + (1-alpha) * l[x]
        res.append(y)
    return res

def avg_calc(l_time, l_data, freq):
    """ applies RMS calculation on a data trace, computational heavy (look to optimize?) """
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    time_step = 1 / freq
    nr_samples = int(time_step / (l_time[1] - l_time[0]))
    incr = 0
    accum = []
    test = 0
    for i in range(len(l_data)):
        if incr < nr_samples:
            test = test + l_data[i]
            accum.append(test/nr_samples)
            incr += 1
        else:
            test = test - l_data[i-nr_samples] + l_data[i]
            accum.append(test/nr_samples)
    return accum

def avg_filter_data(l_time, l_data, avg_rate):
    """ Takes time data and measurement data and averages every 'avg_rate' units 
        Watch out, this reduces the number of data points by a factor of 'avg_rate'!
        Therfore a new time data is return as well:
            returns : [time_data, trace_data] """
    l_time = list(l_time) # list objects calculates faster than Series object
    l_data = list(l_data) # list objects calculates faster than Series object
    if not len(l_time) == len(l_data):
        raise Exception("time and data list do not match in length")
    res_time = []
    res_data = []
    for i in range(0, len(l_data), avg_rate):
        time = 0
        data = 0
        for x in range(0, avg_rate, 1):
            a = i + x
            if a >= len(l_data):
                a = len(l_data) - 1
            time = time + l_time[a]
            data = data + l_data[a]
        res_time.append(time/avg_rate)
        res_data.append(data/avg_rate)
    return [res_time,res_data]