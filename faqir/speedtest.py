import json
from subprocess import Popen, PIPE
from datetime import datetime
from utils import bps_scale, close_processes

# curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
#  2023  sudo apt install speedtest

def main():

    cmd = "speedtest -f json"

    test = Popen(cmd.split(), stdout=PIPE)
    try:
        json_out, _ = test.communicate(30)
    except:
        close_processes(test)
        exit(1)

    json_out=json_out.decode('utf-8')
    dict_out=json.loads(json_out)
    bps = dict_out['download']['bandwidth'] * 8
    test_result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")\
                  +", Vazao: "+bps_scale(bps)\
                  +", Jitter: {} ms, Lost: {} %, Latencia: {} ms, Provedor: {}, Servidor: {}\n"\
                      .format(dict_out['ping']['jitter'],
                              dict_out['packetLoss'],
                              dict_out['ping']['latency'],
                              dict_out['isp'],
                              dict_out['server']['name'])

    file = open("results_speedtest.txt", "a")
    file.write(test_result)
    file.close()

if __name__ == '__main__':
    main()