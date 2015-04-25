#!/usr/bin/env python
# Visualizer for Bug Minimizer
import socket
import json
import sys
import os
import curses

def main(stdscr):
    if(len(sys.argv) < 2):
        print("Socket name is required to run vis.py!")
        exit(-1)

    stdscr.clear()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        print("Trying to connect to %s" % sys.argv[1])
        sock.connect(sys.argv[1])
        print(" SUCCESS")
    except socket.error, msg:
        print(" FAILED")
        print(sys.stderr, msg)
        sys.exit(1)

    data = ""
    jsonstr = ""
    while True:
        # Read data from socket
        while('}' not in data):
            data += sock.recv(4096)
        [jsonstr,data] = data.split('}',1)
        jsonstr += '}'
        info = json.loads(jsonstr)

        # Obtain file information
        try:
            # print("Trying to open file %s" % info['filename'])
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

        line_counter = 0
        bit_counter = 0
        for y in range(stdscr.getyx()[0]+1, curses.LINES):
            line_str = "%d\t" % (line_counter*50)
            while bit_counter < (line_counter+1)*50 and bit_counter < fuzz_file_size:
                line_str += "." if bit_counter not in info['bits'] else "x"
                line_str += " " if bit_counter % 10 == 9 else ""
                bit_counter += 1
            stdscr.addstr(y, 0, line_str)
            line_counter += 1
        stdscr.refresh()
    
curses.wrapper(main)