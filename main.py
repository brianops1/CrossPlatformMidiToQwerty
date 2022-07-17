#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Midi To Qwerty - Type with a midi keyboard

'Midi To Qwerty'

# Programmed by brianops1

__title__ = 'Midi To Qwerty'
__author__ = 'brianops1'
__version__ = '0.0.0'

# packages

#mido
#pynput

from typing import Optional, Union, Final

import os
import re

from threading import Thread
from time import sleep

import mido

from pynput import keyboard
from pynput.keyboard import Key, Controller

# Static variables
BOARD: Final = Controller()

CUR_PORT = None

VELOCITY_MAP: Final = '1234567890qwertyuiopasdfghjklzxc'
LAST_VEL = 'c'

LETTER_NOTE_MAP: Final = '1!2@34$5%6^78*9(0qQwWeErtTyYuiIoOpPasSdDfgGhHjJklLzZxcCvVbBnm'
LOW_NOTES: Final = '1234567890qwert'
HIGH_NOTES: Final = 'yuiopasdfghj'

SUSTAIN_TOGGLE = False
CLOSE_THREAD = False

SETTINGS_FILENAME: Final = 'MidiTranslatorsettings_menu'

# Savable Variables

SETTINGS = {
    'sustainEnabled': True,
    'noDoubles': True,
    'simulateVelocity': True,
    '88Keys': True,
    'sustainCutoff': 63
}

# functions

def ask_int(query: str) -> int:
    "Ask {query} and return number response"
    while True:
        try:
            return int(input(f'{query} : '))
        except ValueError:
            print('\nPlease enter a number.\n')

def select_port() -> str:
    "Return user selected port"
    if CUR_PORT:
        CUR_PORT.close()
    print('Select input device:')
    input_ports = mido.get_input_names()
    for port_num, port_name in enumerate(input_ports):
        print(f'{port_num+1}: {port_name}')
    while True:
        selected_port = ask_int(f'Enter a number from 1 to {len(input_ports)}\n')-1
        if 0 <= selected_port < len(input_ports):
            break
        print('Please select a valid input device.')
    print('Selected {input_ports[selected_port]}')
    return input_ports[selected_port]


def find_velocity_key(velocity: Union[int, float]) -> str:
    "Return key by velocity"
    # lintcheck: global-statement (W0603): Using the global statement
    global LAST_VEL
    idx = round(velocity/4)


    #these while checks are so the program won't hit a note
    #that is pressed just to change velocity
    #At least it should've but it doesn't work :(

##    origin = idx * 4
##    while velocity >= origin - 12:
##        velocity -= 4
##
##    while velocity <= origin + 12:
##        velocity += 4
##    idx = round(velocity/4)

    if idx >= len(VELOCITY_MAP):
        return LAST_VEL
    LAST_VEL = VELOCITY_MAP[idx]
    return LAST_VEL


# lintcheck: too-many-branches (R0912): Too many branches (20/12)
def simulate_key(key_type: str, note: int, velocity: Union[int, float]) -> None:
    "Simulate a key press"
    if not -15 <= note-36 <= 88:
        return None
    index = note - 36

    # C1 is note 36, C6 is note 96
    key = 0 if index >= len(LETTER_NOTE_MAP) else LETTER_NOTE_MAP[index]

    if key_type == 'note_on':
        if SETTINGS['simulateVelocity']:
            velocitykey = find_velocity_key(velocity)
            if velocitykey:
                BOARD.press(Key.alt)
                BOARD.press(velocitykey)
                BOARD.release(velocitykey)
                BOARD.release(Key.alt)

        if 0 <= note-36 <= 60:
            if SETTINGS['noDoubles']:
                if re.search('[!@$%^*(]', key):
                    BOARD.release(LETTER_NOTE_MAP[index-1])
                else:
                    BOARD.release(key.lower())
            if re.search('[!@$%^*(]', key):
                BOARD.press(Key.shift)
                BOARD.press(LETTER_NOTE_MAP[index-1])
                BOARD.release(Key.shift)
            elif key.isupper():
                BOARD.press(Key.shift)
                BOARD.press(key.lower())
                BOARD.release(Key.shift)
            else:
                BOARD.press(key)
        elif SETTINGS['88Keys']:
            key: str
            if note >= 20 and 20 <= note < 40:
                key = LOW_NOTES[note - 21]
            else:
                key = HIGH_NOTES[note - 109]
            # Key is always something because of else branch
            BOARD.release(key)
            BOARD.press(Key.ctrl)
            BOARD.press(key)
            BOARD.release(Key.ctrl)
    else:
        if 0 <= note-36 <= 60:
            if re.search('[!@$%^*(]', key):
                BOARD.release(LETTER_NOTE_MAP[index-1])
            else:
                BOARD.release(key.lower())
        else:
            board_key: str
##            if note >= 20 and note < 40:
            if 40 > note <= 20:
                board_key = LOW_NOTES[note - 21]
            else:
                board_key = HIGH_NOTES[note - 109]
            BOARD.release(board_key)
    return None

def parse_midi(message) -> None:
    "Process message"
    # lintcheck: global-statement (W0603): Using the global statement
    global SUSTAIN_TOGGLE
    if message.type == 'control_change' and SETTINGS['sustainEnabled']:
        if not SUSTAIN_TOGGLE and message.value > SETTINGS['sustainCutoff']:
            SUSTAIN_TOGGLE = True
            BOARD.press(Key.space)
        elif SUSTAIN_TOGGLE and message.value < SETTINGS['sustainCutoff']:
            SUSTAIN_TOGGLE = False
            BOARD.release(Key.space)
    elif message.type in ('note_on', 'note_off'):
        if message.velocity == 0:
            simulate_key('note_off', message.note, message.velocity)
        else:
            simulate_key(message.type, message.note, message.velocity)

def main() -> None:
    "Parse midi messages until CLOSE_THREAD or no more messages."
    # lintcheck: global-statement (W0603): Using the global statement
    global CLOSE_THREAD
    print(f'Now listening to note events on {CUR_PORT}...')
    for message in CUR_PORT:
        parse_midi(message)
        if CLOSE_THREAD:
            break
    CLOSE_THREAD = False


##############################

def settings_menu():
    "Handle settings menu"
    # lintcheck: global-statement (W0603): Using the global statement
    global CUR_PORT
    chang = True
    while chang:
        clear()
        print(f'''
Which settings would you like to change?

0. Back

1. Sustain Enabled ({SETTINGS['sustainEnabled']})

2. Double Notes Disabled ({SETTINGS['noDoubles']})

3. Velocity Enabled ({SETTINGS['simulateVelocity']})

4. 88 Keys Enabled ({SETTINGS['88Keys']})

5. Sustain Pedal Cutoff/Offset ({SETTINGS['sustainCutoff']})

6. Change Midi Port ({str(CUR_PORT)}''')
        selection = ask_int('Value to change: ')
        if 0 > selection > 6:
            print('\nInvalid selection\n')
            sleep(0.5)
            continue

        if selection == 0:
            clear()
            chang = False
        elif selection == 1:
            SETTINGS['sustainEnabled'] = not SETTINGS['sustainEnabled']
        elif selection == 2:
            SETTINGS['noDoubles'] = not SETTINGS['noDoubles']
        elif selection == 3:
            SETTINGS['simulateVelocity'] = not SETTINGS['simulateVelocity']
        elif selection == 4:
            SETTINGS['88Keys'] = not SETTINGS['88Keys']
        elif selection == 5:
            SETTINGS['sustainCutoff'] = ask_int('\nEnter what offset you would like to use (0-127)')
        elif selection == 6:
            CUR_PORT = mido.open_input(select_port())

        save_settings()

def load_settings() -> None:
    "Load settings from file."
    if not os.path.exists(f'{SETTINGS_FILENAME}.txt'):
        save_settings()
        return

    replace: Final = {
        'True': True,
        'False': False
    }

    with open(f'{SETTINGS_FILENAME}.txt', 'r', encoding='utf-8') as file:
        toggle = 0
        change_item = 0
        for line in file.read().splitlines():
            toggle = (toggle + 1) % 2
            if toggle:
                change_item = line
            else:
                try:
                    SETTINGS[change_item] = int(line)
                except ValueError:
                    SETTINGS[change_item] = replace.get(line, line)
        file.close()

####

def save_settings() -> None:
    "Save settings to {SETTINGS_FILENAME}.txt"
    data = []
    for key, value in SETTINGS.items():
        data.append(key)
        data.append(value)
    with open(f'{SETTINGS_FILENAME}.txt', 'w', encoding='utf-8') as file:
        file.write(os.linesep.join(data))
        file.close()

####

def clear() -> None:
    "Call OS clear command"
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# set up key detection #

def detect_key() -> Optional:
    "Detect a key"
    ret_key = None

    def on_release(key) -> Optional[bool]:
        nonlocal ret_key
        if hasattr(key, 'char'):
            ret_key = key
            return False
        return None

    with keyboard.Listener(
        on_press=lambda key_inp: None,
        on_release=on_release
    ) as listener:
        listener.join()

    return ret_key

def run() -> None:
    "Initialize Main"
    # lintcheck: global-statement (W0603): Using the global statement
    global CUR_PORT, CLOSE_THREAD

    try:
        load_settings()
        CUR_PORT = mido.open_input(select_port())

        running = True
        while running:
            clear()
            # lintcheck: line-too-long (C0301): Line too long (105/100)
            print('   ---Welcome to the menu---\n\n\n1. Run main program\n\n2. Settings Menu\n\n3. Exit')
            selection = ask_int('Select Option')
            if 1 > selection > 3:
                selection = None

            if selection:
                clear()
                if selection == 1:
                    while CUR_PORT.poll():
                        pass
                    clear()
                    Thread(target = main).start()
                    sleep(0.5)
                    input('Main code is now running\nhit enter to go back to the menu at any time')
                    CLOSE_THREAD = True
                elif selection == 2:
                    clear()
                    settings_menu()
                else:
                    running = False
            else:
                clear()
                print('There seemed to be an issue')

    # lintcheck: broad-except (W0703): Catching too general exception Exception
    except Exception as ex:
        clear()
        print(f'Error detected: {ex}', file=os.sys.stderr)
        input()
    input('\n\nHit enter now to close. ')

if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.')
    run()
