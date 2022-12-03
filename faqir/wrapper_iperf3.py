import sys
import iperf3

def main():

    c = iperf3.Client()
    c.server_hostname = "localhost"
    # hole punch eh udp
    c.protocol = 'udp'
    c.blksize = 1450
    c.port = int(sys.argv[1])
    if (len(sys.argv) == 3):
        c.bandwidth = int(sys.argv[2])

    result = c.run()
    print(result.jitter_ms)
    print(result.lost_percent)

if __name__ == '__main__':
    main()
