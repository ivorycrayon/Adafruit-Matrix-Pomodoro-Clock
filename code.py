# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Modified for personal use as a study tool at home :)

# Metro Matrix Clock 
# Runs on Airlift Metro M4 with 64x32 RGB Matrix display & shield.

import time
import board
import displayio
import terminalio
import random
import simpleio
from rainbowio import colorwheel
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer

pin_down = DigitalInOut(board.BUTTON_DOWN)
pin_down.switch_to_input(pull=Pull.UP)
button_down = Debouncer(pin_down)
pin_up = DigitalInOut(board.BUTTON_UP)
pin_up.switch_to_input(pull=Pull.UP)
button_up = Debouncer(pin_up)

def get_random_color():
    r = lambda: random.randint(0,255)
    return int('0x%02X%02X%02X' % (r(),r(),r()))

def scroll(line):
    line.x = line.x - 1
    line_width = line.bounding_box[2]
    if line.x < -line_width:
        line.x = display.width

BLINK = True
DEBUG = False
POMODORO = False

buzzer = simpleio.DigitalOut(board.A1,value=0)

test_break_time_interval = .25*60 #5 minute breaks every 25 min
test_big_break_time_interval = .50*60 #30 minute breaks every 90 minutes
test_work_time_interval = .25*60 #25 minute work intervals

break_time_interval = 5.5*60 #5 minute breaks every 25 min
big_break_time_interval = 30*60 #30 minute breaks every 90 minutes
work_time_interval = 25*60 #25 minute work intervals

color_delay = 60*.04 #all times are in seconds
color_delay_fast = 60*.08
color_delay_really_fast = 60*.005
buzzer_beep_duration = 3
color_timer_current = time.time()

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Metro Minimal Clock")
print("Time will be set for {}".format(secrets["timezone"]))

# --- Display setup ---
matrix = Matrix(width=64, height=32)
display = matrix.display
network = Network(status_neopixel=board.NEOPIXEL, debug=False)

# --- Drawing setup ---
clock_group = displayio.Group()  # Create a Group
bitmap = displayio.Bitmap(64, 32, 4)  # Create a bitmap object, width, height, bit depth
color = displayio.Palette(255)  # Create a color palette

for i in range(0, 255):
    color[i] = colorwheel(i)
    #print(color[i])
color[0] = 0x000000

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=color)
clock_group.append(tile_grid)  # Add the TileGrid to the Group
display.show(clock_group)

if not DEBUG:
    font = bitmap_font.load_font("/IBMPlexMono-Medium-24_jep.bdf")
else:
    font = terminalio.FONT

break_label = Label(font,
    color=0x0000ff,
    text="~BREAK~")

break_label.x = 64
break_label.y = 16
break_group = displayio.Group()
break_group.append(break_label)

start_label = Label(font,
    color=0x0000ff,
    text="~POMODORO~")

start_label.x = 64
start_label.y = 16
start_group = displayio.Group()
start_group.append(start_label)

work_label = Label(font,
    color=0xff0000,
    text="??WORK!")

work_label.x = 64
work_label.y = 16
work_group = displayio.Group()
work_group.append(work_label)

clock_label = Label(font, background_color = 0x000000)


color_i = 1

def update_color(color_i):
    clock_label.color = color[color_i]

def update_time(*, hours=None, minutes=None, show_colon=False):
    now = time.localtime()  # Get the time values we need

    if hours is None:
        hours = now[3]

    if hours > 12:  # Handle times later than 12:59
        hours -= 12
    elif not hours:  # Handle times between 0:00 and 0:59
        hours = 12

    if minutes is None:
        minutes = now[4]

    if BLINK:
        colon = ":" if show_colon or now[5] % 2 else " "
    else:
        colon = ":"

    clock_label.text = "{hours}{colon}{minutes:02d}".format(
        hours=hours, minutes=minutes, colon=colon
    )
    bbx, bby, bbwidth, bbh = clock_label.bounding_box
    # Center the label
    clock_label.x = round(display.width / 2 - bbwidth / 2)
    clock_label.y = display.height // 2
    if DEBUG:
        print("Label bounding box: {},{},{},{}".format(bbx, bby, bbwidth, bbh))
        print("Label x: {} y: {}".format(clock_label.x, clock_label.y))


last_check = None
update_time(show_colon=True)  # Display whatever time is on the board
clock_group.append(clock_label)  # add the clock label to the group

break_count = 0

while True:
    button_down.update()
    button_up.update()

    if(button_up.fell):
        POMODORO = True
        start_time = time.time()
        buzzer_start = time.time()
        display.show(start_group)        
        
        while(time.time() - start_time < 10):
            if(time.time() - buzzer_start < .5):
                buzzer.value = True
            else:
                buzzer.value = False
            scroll(start_label)
            time.sleep(.05)
            display.refresh(minimum_frames_per_second=0)

        display.show(clock_group)

    if(button_down.fell):
        POMODORO = False


    if(not POMODORO):
        color_timer_start = time.time()

        update_color(color_i=color_i)

        if(color_i < 254 and color_timer_current - color_timer_start < color_delay):
            color_i += 1
            update_time()
            color_timer_current = time.time()
        else:
            color_i = 1

            if last_check is None or time.monotonic() > last_check + 3600:
                try:
                    update_time(
                        show_colon=True,
                    )  # Make sure a colon is displayed while updating

                    network.get_local_time()  # Synchronize Board's clock to Internet
                    last_check = time.monotonic()
                except RuntimeError as e:
                    print("Some error occured, retrying! -", e)

            update_time()
    else: #POMODORO
        buzzer_start = time.time()
        color_timer_start = time.time()
        display.show(work_group) 
        work_label.x = 64
        while(time.time() - start_time < 28): #7 seconds per loop - 4 loops reminder to work
                if(time.time() - buzzer_start < buzzer_beep_duration):
                    buzzer.value = True
                else:
                    buzzer.value = False
                scroll(work_label)
                work_label.color = 0xff0000
                time.sleep(.04)                
                work_label.color = 0xffffff
                display.refresh(minimum_frames_per_second=0)
        
        display.show(clock_group)

        current_time = time.time()
        work_time = current_time - start_time
        if(work_time > work_time_interval and break_count < 3): #25 min work intervals 
            display.show(break_group)
            break_time = time.time()
            buzzer_start = time.time()

            break_label.x = 64
            while(time.time() - break_time < break_time_interval): #5 min breaks
                if(time.time() - buzzer_start < buzzer_beep_duration):
                    buzzer.value = True
                else:
                    buzzer.value = False
                scroll(break_label)
                time.sleep(.08)
                display.refresh(minimum_frames_per_second=0)

            start_time = time.time()
            break_count += 1
        elif(work_time > work_time_interval and break_count == 3): #25 min work intervals with trigger for the big 4th break
            display.show(break_group)
            break_time = time.time()
            buzzer_start = time.time()

            break_label.x = 64
            while(time.time() - break_time < big_break_time_interval): #15-30 minute rest
                #scroll(break_label)
                #time.sleep(.05)
                if(time.time() - buzzer_start < buzzer_beep_duration):
                    buzzer.value = True
                else:
                    buzzer.value = False
                display.refresh(minimum_frames_per_second=0)

            start_time = time.time()
            break_count = 0

        update_color(color_i=color_i)

        if(color_i < 254 and color_timer_current - color_timer_start < color_delay):
            color_i += 1
            update_time()
            color_timer_current = time.time()
        else:
            color_i = 1

            if last_check is None or time.monotonic() > last_check + 3600:
                try:
                    update_time(
                        show_colon=True,
                    )  # Make sure a colon is displayed while updating

                    network.get_local_time()  # Synchronize Board's clock to Internet
                    last_check = time.monotonic()
                except RuntimeError as e:
                    print("Some error occured, retrying! -", e)

            update_time()
