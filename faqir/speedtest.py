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
        json_out, _ = test.communicate(40)
    except:
        close_processes(test)
        exit(1)

    try:
        json_out=json_out.decode('utf-8')
        dict_out=json.loads(json_out)
        bps = dict_out['download']['bandwidth'] * 8
        test_result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")\
                      +", Download: "+bps_scale(bps)\
                      +", Upload: "+bps_scale(dict_out['upload']['bandwidth'] * 8)\
                      +", Jitter: {} ms, Lost: {} %, Latencia: {} ms, Provedor: {}, Servidor: {}\n"\
                          .format(dict_out['ping']['jitter'] if 'ping' in dict_out.keys() else "0",
                                  dict_out['packetLoss'] if 'packetLoss' in dict_out.keys() else "0",
                                  dict_out['ping']['latency'] if 'ping' in dict_out.keys() else "0",
                                  dict_out['isp'] if 'isp' in dict_out.keys() else "0",
                                  dict_out['server']['name'] if 'server' in dict_out.keys() else "0")

        file = open("results_speedtest.txt", "a")
        file.write(test_result)
        file.close()
    except:
        exit(1)

if __name__ == '__main__':
    main()