#!/usr/bin/env python
# Visualizer for Bug Minimizer
import socket
import json
import sys
import os
import curses
import math
import magic

phaseStr = ['Byte Minimization','Bit Minimization']
sizeStr = ['Bytes','Bits']

def bin(str):
    return ''.join(format(ord(x), '08b') for x in str)

def round_pow10(x):
    return int(10**(math.floor(math.log(2*x,10))))

def ceil_pow10(x):
    if(x < 10):
        return 1
    else:
        return int(10**(math.ceil(math.log(x,10))))

def display_generic(stdscr, phase, info, fuzz_file_size):
    if (phase == 1): # bit minimization mode
        fuzz_file_size *= 8
    sizeUnit = ceil_pow10(fuzz_file_size / (20*50) )
    line_counter = 0
    bit_counter = 0
    for y in xrange(stdscr.getyx()[0]+1, stdscr.getyx()[0]+21):
        if (line_counter*sizeUnit*50 >= fuzz_file_size):
            break
        line_str = "%d\t" % (line_counter*sizeUnit*50)
        while bit_counter < (line_counter+1)*sizeUnit*50 and bit_counter < fuzz_file_size:
            bit_char = "."
            for b in xrange(bit_counter,bit_counter+sizeUnit):
                if b in info['bits']:
                    bit_char = "x"
            line_str += bit_char
            line_str += "|" if (bit_counter/sizeUnit) % 10 == 4 else ""
            line_str += " " if (bit_counter/sizeUnit) % 10 == 9 else ""
            bit_counter += sizeUnit
        stdscr.addstr(y, 0, line_str)
        line_counter += 1

def display_mp3(stdscr, phase, info, fuzz_file, fuzz_file_size):
    header = bin(fuzz_file.read(4))

    frameSync = int(header[0:11],2)
    MPEGverID = int(header[11:13],2) # 00 - MPEG Version 2.5 (unofficial), 01 - reserved, 10 - MPEG Version 2 (ISO/IEC 13818-3), 11 - MPEG Version 1 (ISO/IEC 11172-3)
    layerDesc = int(header[13:15],2) # 00 - reserved, 01 - Layer III, 10 - Layer II, 11 - Layer I
    protectionBit = int(header[15],2)
    bitRateIdx = int(header[16:20],2)
    frequencyIdx = int(header[20:22],2)
    padding = int(header[22],2)
    channelMode = int(header[24:26],2)

    # bitrates are in kbps
    if (MPEGverID == 3 and layerDesc == 3): # V1, L1
        bitRateTable = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, -1]
    elif (MPEGverID == 3 and layerDesc == 2): # V1, L2
        bitRateTable = [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, -1]
    elif (MPEGverID == 3 and layerDesc == 1): # V1, L3
        bitRateTable = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, -1]
    elif (MPEGverID == 2 and layerDesc == 3): # V2, L1
        bitRateTable == [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, -1]
    elif (MPEGverID == 2 and (layerDesc == 2 or layerDesc == 1)):
        bitRateTable = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, -1]
    bitRate = bitRateTable[bitRateIdx]*1000

    freqTable = [[11025, 12000, 8000], [-1,-1,-1], [22050, 24000, 16000], [44100, 48000, 32000]] # [MPEG Version 2.5, reserved, MPEG Version 2, MPEG Version 1]
    sampleFreq = freqTable[MPEGverID][frequencyIdx]

    frameSize = 144 * bitRate / (sampleFreq + padding)
    if (channelMode == 3): # if file is in mono, halve the amount of data
        frameSize /= 2
    frameDataSize = frameSize - 4

    numFrames = fuzz_file_size / frameSize
    stdscr.addstr(stdscr.getyx()[0]+1,0,"# Total Frames: %d" % numFrames)

    bitMode = 1 if phase == 0 else 8
    frameSize *= 1 if phase == 0 else 8

    frameHeaders = [['.']*4*bitMode for x in xrange(numFrames)]
    frameData = [['.']*10 for x in xrange(numFrames)]
    for b in info['bits']:
        try:
            if(b % frameSize < (4*bitMode)):
                frameHeaders[b/frameSize][b % frameSize] = 'x'
            else:
                frameData[b/frameSize][(b % frameSize) % 10] = 'x'
        except:
            pass

    ypos = stdscr.getyx()[0]
    xpos = 0
    for f in xrange(numFrames):
        if stdscr.getyx()[0]+1 >= curses.LINES:
            if xpos == curses.COLS/2:
                break
            else:
                xpos = curses.COLS/2
                stdscr.move(ypos,xpos)
        if 'x' in frameHeaders[f]:
            stdscr.addstr(stdscr.getyx()[0]+1,xpos,"FrameHeader\t#%d:\t%s" % (f,''.join(frameHeaders[f])))
        elif 'x' in frameData[f]:
            stdscr.addstr(stdscr.getyx()[0]+1,xpos,"FrameData\t#%d:\t%s" % (f,''.join(frameData[f])))

def main(stdscr):
    if(len(sys.argv) < 2):
        print("Socket name is required to run vis.py!")
        exit(-1)

    stdscr.clear()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

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
    phase = 0
    prevNumbits = sys.maxint
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
        info = json.loads(jsonstr+'}')

        if (info['stage'] == 'fin'):
            break

        # Obtain file information
        try:
            fuzz_file = open(info['filename'],'r')
            fuzz_file_info = os.stat(info['filename'])
            fuzz_file_size = fuzz_file_info.st_size
            fuzz_file_type = magic.from_file(info['filename'],mime=True)
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
            sys.exit(-1)
        except ValueError:
            print "Could not convert data to an integer."
            sys.exit(-1)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            sys.exit(-1)

        # Determine current phase
        if(prevNumbits < info['numbits']):
            phase = 1

        stdscr.clear()
        # Print status information
        stdscr.addstr(0,0,"Bug minimization for %s" % info['filename'], curses.color_pair(1))
        stdscr.addstr(stdscr.getyx()[0]+1,0,"File type: %s" % fuzz_file_type, curses.color_pair(1))
        stdscr.addstr(stdscr.getyx()[0]+1,0,"Current Phase: %s" % phaseStr[phase], curses.color_pair(2))
        stdscr.addstr(stdscr.getyx()[0]+1,0,"File size: %d %s" % (fuzz_file_size if phase == 0 else fuzz_file_size*8, sizeStr[phase]))
        stdscr.addstr(stdscr.getyx()[0]+1,0,"# Candidate %s: %d" % (sizeStr[phase], info['numbits']))
        prevNumbits = info['numbits']

        if (fuzz_file_type == 'audio/mpeg'):
            display_mp3(stdscr, phase, info, fuzz_file, fuzz_file_size)
        else:
            display_generic(stdscr, phase, info, fuzz_file_size)
        stdscr.refresh()

curses.wrapper(main)