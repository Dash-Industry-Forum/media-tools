import os, sys
from optparse import OptionParser

def main():
    parser = OptionParser(usage="%prog [options]", description="Create .ccs file with rolling timestamps every second")
    parser.add_option('-d', '--dur', help='duration in seconds [default: %default]',
       type='int', action='store', default=10, dest='duration')
    parser.add_option('-l', '--language', help='language [default: %default]',
       type='string', action='store', default="eng", dest='lang')
    (opts, _) = parser.parse_args()
    secs = 0
    line_nrs = (1, 2, 3, 4, 5, 10, 11, 12, 13, 14)
    colors = ("white", "green", "blue", "cyan", "red", "yellow", "magenta", "italics")
    while secs < opts.duration:
        line_nr = line_nrs[secs % len(line_nrs)]
        color = colors[secs % len(colors)]
        minutes, seconds = divmod(secs, 60)
        print("00:%02d:%02d:00" % (minutes, seconds))
        print("> RCL ENM PAC_%d_%s" % (line_nr, color))
        print("%s: 00:%02d:%02d:00" % (opts.lang, minutes, seconds))
        print("> EDM EOC")
        print("")
        secs += 1

if __name__ == "__main__":
    main() 