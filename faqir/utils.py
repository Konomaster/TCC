import psutil

def close_processes(pid_list):
    for pid in pid_list:
        if not psutil.pid_exists(pid):
            continue
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except:
                pass
        try:
            parent.kill()
        except:
            pass

def bps_scale(bps):
    result_string = str(bps)
    i = 0
    unit = -1
    point = 0
    while i < len(result_string):
        if i % 3 == 0 and unit < 8:
            unit += 1
            point = i
        i += 1
    if point > 2:
        result_string = result_string[:len(result_string) - point] + "." + result_string[
                                                                           len(result_string) - point:]
    if unit < 1:
        result_string = result_string + " bits/s"
    elif unit == 1:
        result_string = result_string + " Kbits/s"
    elif unit == 2:
        result_string = result_string + " Mbits/s"
    elif unit == 3:
        result_string = result_string + " Gbits/s"
    elif unit == 4:
        result_string = result_string + " Tbits/s"
    elif unit == 5:
        result_string = result_string + " Pbits/s"
    elif unit == 6:
        result_string = result_string + " Ebits/s"
    elif unit == 7:
        result_string = result_string + " Zbits/s"
    elif unit == 8:
        result_string = result_string + " Ybits/s"

    return result_string