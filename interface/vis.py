#!/usr/bin/env python
# Visualizer for Bug Minimizer
import socket
import json
import sys
import os
import curses
import math

def round_pow10(x):
    return int(10**(math.floor(math.log(2*x,10))))

def ceil_pow10(x):
    return int(10**(math.ceil(math.log(x,10))))

def main(stdscr):
    if(len(sys.argv) < 2):
        print("Socket name is required to run vis.py!")
        exit(-1)

    stdscr.clear()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sys.stdout.write("Trying to connect to %s...\t" % sys.argv[1])
        sock.connect(sys.argv[1])
        print("SUCCESS")
    except socket.error, msg:
        print("FAILED")
        print(sys.stderr, msg)
        sys.exit(1)

    data = ""
    jsonstr = ""
    while True:
        # Receive keyboard command
        stdscr.nodelay(1) # non-blocking keyboard input
        key = stdscr.getch()
        if key == ord('q'):
            break

        # Read data from socket
        while('}' not in data):
            data += sock.recv(4096)
        [jsonstr,data] = data.split('}',1)
        jsonstr += '}'
        info = json.loads(jsonstr)

        # Obtain file information
        try:
            fuzz_file = open(info['filename'],'r')
            fuzz_file_info = os.stat(info['filename'])
            fuzz_file_size = fuzz_file_info.st_size
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
            sys.exit(-1)
        except ValueError:
            print "Could not convert data to an integer."
            sys.exit(-1)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            sys.exit(-1)

        # Print status information
        stdscr.addstr(0,0,"Bug minimization for %s" % info['filename'], curses.color_pair(1))
        stdscr.addstr(stdscr.getyx()[0]+1,0,"File size: %d bytes" % fuzz_file_size)
        stdscr.addstr(stdscr.getyx()[0]+1,0,"# Bits: %d" % info['numbits'])

        sizeUnit = ceil_pow10(fuzz_file_size / (20*50) )
        stdscr.addstr(stdscr.getyx()[0]+1,0,"sizeUnit: %d" % sizeUnit)
        line_counter = 0
        bit_counter = 0
        for y in range(stdscr.getyx()[0]+1, stdscr.getyx()[0]+21):
            if (line_counter*sizeUnit*50 > fuzz_file_size):
                break
            line_str = "%d\t" % (line_counter*sizeUnit*50)
            while bit_counter < (line_counter+1)*sizeUnit*50 and bit_counter < fuzz_file_size:
                bit_char = "."
                for b in range(bit_counter,bit_counter+sizeUnit):
                    if b in info['bits']:
                        bit_char = "x"
                line_str += bit_char
                line_str += " " if (bit_counter/sizeUnit) % 10 == 9 else ""
                bit_counter += sizeUnit
            stdscr.addstr(y, 0, line_str)
            line_counter += 1
        stdscr.refresh()
    
curses.wrapper(main)